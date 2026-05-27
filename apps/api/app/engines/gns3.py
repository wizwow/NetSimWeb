"""GNS3 simulation engine adapter.

All GNS3 HTTP interactions are encapsulated here.
No other module may call GNS3 directly (ARCHITECTURE.md §3.2).
"""

import asyncio
import json
import re
from collections import defaultdict
from typing import Any, Mapping

import httpx

from app.engines.base import SimulationEngineInterface
from app.schemas.engine_plan import (
    EngineDeploymentPlanSchema,
    EngineLinkPlanSchema,
    EngineNodePlanSchema,
)
from app.schemas.topology import (
    FaultType,
    NodeStatus,
    ProbeResultSchema,
    ProbeType,
    TopologyBase,
)
from app.services.topology_translator import translate_topology_to_engine_plan


class GNS3AdapterError(RuntimeError):
    """Raised when GNS3 mode cannot complete an adapter operation."""


# ---------------------------------------------------------------------------
# Registry types used for in-memory & persistent ID mappings
# ---------------------------------------------------------------------------

class _NodeEntry:
    """Tracks a single node's GNS3 coordinates."""

    __slots__ = ("project_id", "gns3_node_id", "next_adapter", "base_type", "vendor")

    def __init__(
        self,
        project_id: str,
        gns3_node_id: str,
        base_type: str = "router",
        vendor: str | None = None,
    ) -> None:
        self.project_id = project_id
        self.gns3_node_id = gns3_node_id
        self.next_adapter = 0  # monotonically incremented per link
        self.base_type = base_type
        self.vendor = vendor

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "gns3_node_id": self.gns3_node_id,
            "next_adapter": self.next_adapter,
            "base_type": self.base_type,
            "vendor": self.vendor,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "_NodeEntry":
        entry = cls(
            data["project_id"],
            data["gns3_node_id"],
            base_type=data.get("base_type", "router"),
            vendor=data.get("vendor"),
        )
        entry.next_adapter = data.get("next_adapter", 0)
        return entry


class _LinkEntry:
    """Tracks a single link's GNS3 coordinates."""

    __slots__ = ("project_id", "gns3_link_id")

    def __init__(self, project_id: str, gns3_link_id: str) -> None:
        self.project_id = project_id
        self.gns3_link_id = gns3_link_id

    def to_dict(self) -> dict:
        return {"project_id": self.project_id, "gns3_link_id": self.gns3_link_id}

    @classmethod
    def from_dict(cls, data: dict) -> "_LinkEntry":
        return cls(data["project_id"], data["gns3_link_id"])


class GNS3SimulationEngine(SimulationEngineInterface):
    """Adapter for a self-hosted GNS3 Server."""

    def __init__(
        self,
        base_url: str,
        user: str,
        password: str,
        template_mappings: Mapping[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.password = password
        self.template_mappings = dict(template_mappings or {})

        # In-memory registries — populated by create_topology / load_registries
        self._node_registry: dict[str, _NodeEntry] = {}
        self._link_registry: dict[str, _LinkEntry] = {}

    # ------------------------------------------------------------------
    # Registry persistence helpers (called by SimulationService)
    # ------------------------------------------------------------------

    def export_registries(self) -> dict[str, Any]:
        """Serialise registries for DB persistence."""
        return {
            "nodes": {k: v.to_dict() for k, v in self._node_registry.items()},
            "links": {k: v.to_dict() for k, v in self._link_registry.items()},
        }

    def load_registries(self, data: dict[str, Any] | None) -> None:
        """Restore registries from a previously-exported dict."""
        if not data:
            return
        self._node_registry = {
            k: _NodeEntry.from_dict(v) for k, v in data.get("nodes", {}).items()
        }
        self._link_registry = {
            k: _LinkEntry.from_dict(v) for k, v in data.get("links", {}).items()
        }

    # ------------------------------------------------------------------
    # SimulationEngineInterface — topology lifecycle
    # ------------------------------------------------------------------

    async def create_topology(self, topology: TopologyBase) -> str:
        plan = translate_topology_to_engine_plan(topology)
        self._ensure_templates_available(plan)

        # Fetch templates from GNS3 to extract their node types
        template_type_map: dict[str, str] = {}
        try:
            gns3_templates = await self._request("GET", "/v2/templates")
            for tpl in gns3_templates:
                tpl_id = tpl.get("template_id") or tpl.get("id")
                tpl_type = tpl.get("template_type") or tpl.get("type") or "qemu"
                if tpl_id:
                    template_type_map[str(tpl_id)] = str(tpl_type)
        except Exception:
            # Fall back to sensible mappings if GNS3 templates query fails
            pass

        # 1. Create GNS3 project
        import uuid
        payload = {"name": f"{plan.name} - {uuid.uuid4().hex[:8]}"}
        project = await self._request("POST", "/v2/projects", json=payload)
        project_id = (
            project.get("project_id") or project.get("projectId") or project.get("id")
        )
        if not project_id:
            raise GNS3AdapterError(
                "GNS3 project creation response did not include a project id"
            )
        project_id = str(project_id)

        # 2. Create nodes inside the project
        node_id_map = await self._provision_nodes(project_id, plan, template_type_map)

        # 3. Create links inside the project
        await self._provision_links(project_id, plan, node_id_map)

        return project_id

    async def start_topology(self, engine_topology_id: str) -> None:
        await self._request(
            "POST", f"/v2/projects/{engine_topology_id}/nodes/start",
        )

    async def stop_topology(self, engine_topology_id: str) -> None:
        await self._request(
            "POST", f"/v2/projects/{engine_topology_id}/nodes/stop",
        )

    async def delete_topology(self, engine_topology_id: str) -> None:
        await self._request(
            "DELETE", f"/v2/projects/{engine_topology_id}",
        )

    # ------------------------------------------------------------------
    # SimulationEngineInterface — node status
    # ------------------------------------------------------------------

    async def get_node_status(self, engine_node_id: str) -> NodeStatus:
        entry = self._node_registry.get(engine_node_id)
        if entry is None:
            # Fallback: legacy synthetic format "<label>:<status>"
            status = engine_node_id.rsplit(":", 1)[-1].lower()
            return self._map_node_status(status)

        node_data = await self._request(
            "GET",
            f"/v2/projects/{entry.project_id}/nodes/{entry.gns3_node_id}",
        )
        return self._map_node_status(node_data.get("status", "unknown"))

    # ------------------------------------------------------------------
    # SimulationEngineInterface — fault injection
    # ------------------------------------------------------------------

    async def inject_fault(self, engine_link_id: str, fault: FaultType) -> None:
        entry = self._link_registry.get(engine_link_id)
        if entry is None:
            raise GNS3AdapterError(
                f"Link '{engine_link_id}' not found in GNS3 registry. "
                "Has the topology been provisioned?"
            )

        update_payload: dict[str, Any]
        if fault == "link-down":
            update_payload = {"suspend": True}
        elif fault == "high-latency":
            update_payload = {"filters": {"delay": [150]}}
        elif fault == "packet-loss":
            update_payload = {"filters": {"packet_loss": [25]}}
        else:
            raise GNS3AdapterError(f"Unsupported fault type: {fault}")

        await self._request(
            "PUT",
            f"/v2/projects/{entry.project_id}/links/{entry.gns3_link_id}",
            json=update_payload,
        )

    async def clear_fault(self, engine_link_id: str) -> None:
        """Remove any active fault (suspend + filters) from a link."""
        entry = self._link_registry.get(engine_link_id)
        if entry is None:
            raise GNS3AdapterError(
                f"Link '{engine_link_id}' not found in GNS3 registry. "
                "Has the topology been provisioned?"
            )
        await self._request(
            "PUT",
            f"/v2/projects/{entry.project_id}/links/{entry.gns3_link_id}",
            json={"suspend": False, "filters": {}},
        )

    # ------------------------------------------------------------------
    # SimulationEngineInterface — probe execution
    # ------------------------------------------------------------------

    async def run_probe(
        self, source_node_id: str, target_ip: str, probe_type: ProbeType,
    ) -> ProbeResultSchema:
        entry = self._node_registry.get(source_node_id)
        if entry is None:
            raise GNS3AdapterError(
                f"Node '{source_node_id}' not found in GNS3 registry. "
                "Has the topology been provisioned?"
            )

        command = self._probe_command(
            target_ip, probe_type, base_type=entry.base_type, vendor=entry.vendor
        )
        output = await self._exec_console_command(
            entry.project_id, entry.gns3_node_id, command,
        )
        return self._parse_probe_output(
            output, probe_type, base_type=entry.base_type, vendor=entry.vendor
        )

    # ------------------------------------------------------------------
    # Internal — HTTP helper
    # ------------------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(
                auth=(self.user, self.password), timeout=15.0,
            ) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            detail = ""
            try:
                if "response" in locals() and response is not None and response.content:
                    detail = f" | Response: {response.text}"
            except Exception:
                pass
            raise GNS3AdapterError(
                f"GNS3 request failed: {method} {url}: {exc}{detail}"
            ) from exc

        if not response.content:
            return {}
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise GNS3AdapterError(
                f"GNS3 returned invalid JSON for {method} {url}"
            ) from exc

    # ------------------------------------------------------------------
    # Internal — node provisioning
    # ------------------------------------------------------------------

    async def _provision_nodes(
        self,
        project_id: str,
        plan: EngineDeploymentPlanSchema,
        template_type_map: dict[str, str],
    ) -> dict[str, str]:
        """Create all nodes in GNS3.  Returns {netsimflow_id: gns3_node_id}."""
        node_id_map: dict[str, str] = {}
        for node in plan.nodes:
            payload = self._build_node_payload(node)
            
            # Resolve node_type
            template_id = payload.get("template_id")
            node_type = template_type_map.get(str(template_id))
            if not node_type:
                # Sensible fallbacks
                if node.baseType == "switch":
                    node_type = "ethernet_switch"
                elif node.baseType == "host":
                    node_type = "vpcs"
                elif node.baseType == "cloud":
                    node_type = "cloud"
                else:
                    node_type = "qemu"
            payload["node_type"] = node_type

            # Ethernet switches/hubs do not allow custom properties in GNS3 schema
            if node_type in {"ethernet_switch", "ethernet_hub"}:
                payload.pop("properties", None)

            result = await self._request(
                "POST", f"/v2/projects/{project_id}/nodes", json=payload,
            )
            gns3_nid = (
                result.get("node_id") or result.get("id") or ""
            )
            if not gns3_nid:
                raise GNS3AdapterError(
                    f"GNS3 node creation for '{node.label}' did not return a node id"
                )
            gns3_nid = str(gns3_nid)
            node_id_map[node.id] = gns3_nid
            self._node_registry[node.id] = _NodeEntry(
                project_id, gns3_nid, base_type=node.baseType, vendor=node.vendor
            )
        return node_id_map

    # ------------------------------------------------------------------
    # Internal — link provisioning
    # ------------------------------------------------------------------

    async def _provision_links(
        self,
        project_id: str,
        plan: EngineDeploymentPlanSchema,
        node_id_map: dict[str, str],
    ) -> None:
        """Create all links in GNS3, tracking adapter/port counters."""
        port_counters: dict[str, int] = defaultdict(int)
        node_types = {node.id: node.baseType for node in plan.nodes}
        for link in plan.links:
            payload = self._build_link_payload_tracked(
                link, node_id_map, port_counters, node_types
            )
            result = await self._request(
                "POST", f"/v2/projects/{project_id}/links", json=payload,
            )
            gns3_lid = result.get("link_id") or result.get("id") or ""
            if not gns3_lid:
                raise GNS3AdapterError(
                    f"GNS3 link creation for '{link.id}' did not return a link id"
                )
            self._link_registry[link.id] = _LinkEntry(project_id, str(gns3_lid))

    # ------------------------------------------------------------------
    # Internal — console / probe helpers
    # ------------------------------------------------------------------

    async def _exec_console_command(
        self, project_id: str, gns3_node_id: str, command: str,
    ) -> str:
        """Run *command* on a node via the GNS3 console HTTP endpoint.

        GNS3 exposes ``POST /v2/compute/projects/{pid}/docker/nodes/{nid}/console``
        for Docker-based nodes and a Telnet port for appliance nodes.  We attempt
        the HTTP console first (simplest, no raw socket needed).  If the endpoint
        does not exist, we fall back to reading the ``console`` + ``console_host``
        fields and opening a raw Telnet session.
        """
        # Fast-path: HTTP console (Docker / QEMU with API console support)
        try:
            result = await self._request(
                "POST",
                f"/v2/projects/{project_id}/nodes/{gns3_node_id}/console",
                json={"command": command},
            )
            return result.get("output", "")
        except GNS3AdapterError:
            pass  # endpoint may not exist — fall through to Telnet

        # Slow-path: Telnet console
        node_info = await self._request(
            "GET", f"/v2/projects/{project_id}/nodes/{gns3_node_id}",
        )
        console_port = node_info.get("console")
        console_host = node_info.get("console_host") or "127.0.0.1"
        if not console_port:
            raise GNS3AdapterError(
                f"Node {gns3_node_id} has no console port; cannot execute probe"
            )

        return await self._telnet_command(console_host, int(console_port), command)

    @staticmethod
    async def _telnet_command(host: str, port: int, command: str) -> str:
        """Open a brief Telnet session, send *command*, return the output."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=5.0,
            )
        except (OSError, asyncio.TimeoutError) as exc:
            raise GNS3AdapterError(
                f"Cannot connect to console at {host}:{port}: {exc}"
            ) from exc

        try:
            # Drain any login banner
            await asyncio.sleep(0.5)
            try:
                await asyncio.wait_for(reader.read(4096), timeout=1.0)
            except asyncio.TimeoutError:
                pass

            writer.write(f"{command}\n".encode())
            await writer.drain()

            # Collect output until idle
            chunks: list[bytes] = []
            while True:
                try:
                    chunk = await asyncio.wait_for(reader.read(4096), timeout=3.0)
                    if not chunk:
                        break
                    chunks.append(chunk)
                except asyncio.TimeoutError:
                    break
            return b"".join(chunks).decode(errors="replace")
        finally:
            writer.close()

    @staticmethod
    def _probe_command(
        target_ip: str,
        probe_type: ProbeType,
        base_type: str = "router",
        vendor: str | None = None,
    ) -> str:
        if vendor == "cisco":
            if probe_type == "traceroute":
                return f"traceroute {target_ip}"
            return f"ping {target_ip} repeat 3"

        if base_type == "host":
            if probe_type == "traceroute":
                return f"trace {target_ip}"
            return f"ping {target_ip} -c 3"

        # default/Linux
        if probe_type == "traceroute":
            return f"traceroute -w 2 {target_ip}"
        return f"ping -c 3 {target_ip}"

    @staticmethod
    def _parse_probe_output(
        raw: str,
        probe_type: ProbeType,
        base_type: str = "router",
        vendor: str | None = None,
    ) -> ProbeResultSchema:
        if probe_type == "traceroute":
            hops: list[dict[str, Any]] = []
            for line in raw.splitlines():
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+([\d.]+)\s*ms(?:ec)?", line)
                if m:
                    hops.append({"ip": m.group(1), "rttMs": float(m.group(2))})
            return ProbeResultSchema(
                success=len(hops) > 0,
                output=raw.strip(),
                hops=hops or None,
            )

        # ping
        if vendor == "cisco":
            success_match = re.search(r"Success rate is (\d+) percent", raw, re.IGNORECASE)
            success = int(success_match.group(1)) > 0 if success_match else False
            rtt_match = re.search(r"min/avg/max\s*=\s*\d+/(\d+)/\d+\s*ms(?:ec)?", raw, re.IGNORECASE)
            rtt = float(rtt_match.group(1)) if rtt_match else None
            return ProbeResultSchema(success=success, output=raw.strip(), rttMs=rtt)

        # default ping (Linux, VPCS)
        rtt_match = re.search(r"[/=](\d+(?:\.\d+)?)(?:/|\s*ms)", raw)
        rtt = float(rtt_match.group(1)) if rtt_match else None
        success = "bytes from" in raw.lower() or "ttl=" in raw.lower()
        return ProbeResultSchema(success=success, output=raw.strip(), rttMs=rtt)

    # ------------------------------------------------------------------
    # Internal — template / payload helpers
    # ------------------------------------------------------------------

    def _ensure_templates_available(self, plan: EngineDeploymentPlanSchema) -> None:
        missing_kinds = sorted({
            node.engineKind
            for node in plan.nodes
            if node.engineKind in {"network-device", "host", "cloud", "site"}
            and node.engineKind not in self.template_mappings
        })
        if missing_kinds:
            missing = ", ".join(missing_kinds)
            raise GNS3AdapterError(
                "GNS3 template mappings are required before creating nodes for: "
                f"{missing}. Configure template mappings before using SIMULATION_ENGINE=gns3."
            )

    def _resolve_template_id(self, node: EngineNodePlanSchema) -> str:
        template_id = self.template_mappings.get(node.engineKind)
        if not template_id:
            raise GNS3AdapterError(
                "GNS3 template mapping missing for "
                f"engine kind '{node.engineKind}' while preparing node '{node.label}'. "
                f"Configure GNS3_TEMPLATE_MAPPINGS with a '{node.engineKind}' entry."
            )
        return template_id

    def _build_node_payload(self, node: EngineNodePlanSchema) -> dict:
        template_id = self._resolve_template_id(node)
        return {
            "name": node.label,
            "template_id": template_id,
            "x": 0,
            "y": 0,
            "compute_id": "local",
        }

    @staticmethod
    def _build_link_payload(
        link: EngineLinkPlanSchema,
        node_id_map: Mapping[str, str],
    ) -> dict:
        """Build a link payload with adapter/port 0.  Used by existing tests."""
        try:
            source_gns3_id = node_id_map[link.sourceNodeId]
            target_gns3_id = node_id_map[link.targetNodeId]
        except KeyError as exc:
            raise GNS3AdapterError(
                f"Cannot build GNS3 link payload for '{link.id}': "
                f"missing node mapping for {exc.args[0]}"
            ) from exc

        return {
            "nodes": [
                {
                    "node_id": source_gns3_id,
                    "adapter_number": 0,
                    "port_number": 0,
                    "label": {"text": link.sourcePort},
                },
                {
                    "node_id": target_gns3_id,
                    "adapter_number": 0,
                    "port_number": 0,
                    "label": {"text": link.targetPort},
                },
            ],
            "filters": {},
            "suspend": bool(link.faultState and link.faultState.get("active")),
        }

    @staticmethod
    def _build_link_payload_tracked(
        link: EngineLinkPlanSchema,
        node_id_map: Mapping[str, str],
        port_counters: dict[str, int],
        node_types: Mapping[str, str] | None = None,
    ) -> dict:
        """Build a link payload with auto-incrementing adapter/port numbers."""
        try:
            source_gns3_id = node_id_map[link.sourceNodeId]
            target_gns3_id = node_id_map[link.targetNodeId]
        except KeyError as exc:
            raise GNS3AdapterError(
                f"Cannot build GNS3 link payload for '{link.id}': "
                f"missing node mapping for {exc.args[0]}"
            ) from exc

        types = node_types or {}

        # Source node
        src_type = types.get(link.sourceNodeId, "router")
        src_val = port_counters[link.sourceNodeId]
        port_counters[link.sourceNodeId] += 1
        if src_type == "switch":
            src_adapter = 0
            src_port = src_val
        else:
            src_adapter = src_val
            src_port = 0

        # Target node
        tgt_type = types.get(link.targetNodeId, "router")
        tgt_val = port_counters[link.targetNodeId]
        port_counters[link.targetNodeId] += 1
        if tgt_type == "switch":
            tgt_adapter = 0
            tgt_port = tgt_val
        else:
            tgt_adapter = tgt_val
            tgt_port = 0

        return {
            "nodes": [
                {
                    "node_id": source_gns3_id,
                    "adapter_number": src_adapter,
                    "port_number": src_port,
                    "label": {"text": link.sourcePort},
                },
                {
                    "node_id": target_gns3_id,
                    "adapter_number": tgt_adapter,
                    "port_number": tgt_port,
                    "label": {"text": link.targetPort},
                },
            ],
            "filters": {},
            "suspend": bool(link.faultState and link.faultState.get("active")),
        }

    @staticmethod
    def _map_node_status(status: str) -> NodeStatus:
        if status in {"started", "running"}:
            return "running"
        if status in {"stopped", "closed"}:
            return "stopped"
        if status in {"suspended"}:
            return "degraded"
        if status in {"starting"}:
            return "booting"
        return "error"
