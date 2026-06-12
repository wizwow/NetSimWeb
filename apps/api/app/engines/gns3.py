"""GNS3 simulation engine adapter.

All GNS3 HTTP interactions are encapsulated here.
No other module may call GNS3 directly (ARCHITECTURE.md §3.2).
"""

import json
import logging
from typing import Mapping

import httpx

from app.engines.base import SimulationEngineInterface
from app.schemas.engine_plan import (
    EngineLinkPlanSchema,
    EngineNodePlanSchema,
    TopologyProvisioningResult,
)
from app.schemas.topology import (
    FaultType,
    NodeStatus,
    ProbeResultSchema,
    ProbeType,
    TopologyBase,
)
from app.services.topology_translator import translate_topology_to_engine_plan


logger = logging.getLogger(__name__)


class GNS3AdapterError(RuntimeError):
    """Raised when GNS3 mode cannot complete an adapter operation."""


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

    async def create_topology(self, topology: TopologyBase) -> TopologyProvisioningResult:
        plan = translate_topology_to_engine_plan(topology)
        self._ensure_templates_available(plan)

        # 1. Create the project.
        payload = {"name": plan.name}
        project = await self._request("POST", "/v2/projects", json=payload)
        project_id = project.get("project_id") or project.get("projectId") or project.get("id")
        if not project_id:
            raise GNS3AdapterError("GNS3 project creation response did not include a project id")
        project_id = str(project_id)

        # 2. Provision each node. On partial failure we best-effort delete
        #    the half-provisioned project so the next start does not see
        #    stale orphan nodes. The original error is always re-raised.
        node_id_map: dict[str, str] = {}
        try:
            for node in plan.nodes:
                node_payload = self._build_node_payload(node)
                response = await self._request(
                    "POST", f"/v2/projects/{project_id}/nodes", json=node_payload
                )
                gns3_node_id = response.get("node_id") or response.get("nodeId")
                if not gns3_node_id:
                    raise GNS3AdapterError(
                        "GNS3 node creation response for "
                        f"'{node.label}' did not include a node id"
                    )
                node_id_map[node.id] = str(gns3_node_id)
        except Exception:
            await self._safe_delete_project(project_id)
            raise

        # 3. Provision each link. The link payload is built from the
        #    already-provisioned node_id_map (each endpoint must be
        #    translated to a real GNS3 node id), so any missing mapping
        #    surfaces as an adapter error here. On partial failure we
        #    best-effort delete the whole project — there is no value in
        #    keeping a project with half its links provisioned because
        #    the next start would skip re-provisioning and the user
        #    would see phantom links in the canvas that don't actually
        #    exist in GNS3.
        link_id_map: dict[str, str] = {}
        try:
            for link in plan.links:
                link_payload = self._build_link_payload(link, node_id_map)
                response = await self._request(
                    "POST", f"/v2/projects/{project_id}/links", json=link_payload
                )
                gns3_link_id = response.get("link_id") or response.get("linkId")
                if not gns3_link_id:
                    raise GNS3AdapterError(
                        "GNS3 link creation response for "
                        f"'{link.id}' did not include a link id"
                    )
                link_id_map[link.id] = str(gns3_link_id)
        except Exception:
            await self._safe_delete_project(project_id)
            raise

        return TopologyProvisioningResult(
            engine_topology_id=project_id,
            node_id_map=node_id_map,
            link_id_map=link_id_map,
        )

    async def _safe_delete_project(self, project_id: str) -> None:
        """Best-effort delete used during partial-failure cleanup.

        Any error is logged (so operators can see when the GNS3 server
        itself is the failure) but never re-raised — we only call this
        from a recovery path and the original failure is what the
        caller needs to see. Uses a short timeout so a hung GNS3
        server does not delay the user-facing error.
        """
        try:
            await self._request(
                "DELETE", f"/v2/projects/{project_id}", timeout=3.0
            )
        except GNS3AdapterError as exc:
            logger.warning(
                "Failed to clean up half-provisioned GNS3 project %s: %s",
                project_id,
                exc,
            )

    async def start_topology(self, engine_topology_id: str) -> None:
        await self._request("POST", f"/v2/projects/{engine_topology_id}/open")

    async def stop_topology(self, engine_topology_id: str) -> None:
        await self._request("POST", f"/v2/projects/{engine_topology_id}/close")

    async def start_node(
        self, engine_topology_id: str, engine_node_id: str
    ) -> None:
        await self._request(
            "POST",
            f"/v2/projects/{engine_topology_id}/nodes/{engine_node_id}/start",
        )

    async def stop_node(
        self, engine_topology_id: str, engine_node_id: str
    ) -> None:
        await self._request(
            "POST",
            f"/v2/projects/{engine_topology_id}/nodes/{engine_node_id}/stop",
        )

    async def get_node_status(
        self, engine_topology_id: str, engine_node_id: str
    ) -> NodeStatus:
        response = await self._request(
            "GET", f"/v2/projects/{engine_topology_id}/nodes/{engine_node_id}"
        )
        raw = (response.get("status") or "unknown").lower()
        return self._map_node_status(raw)

    async def inject_fault(self, engine_link_id: str, fault: FaultType) -> None:
        raise NotImplementedError("GNS3 fault injection requires link suspend mapping")

    async def run_probe(
        self, source_node_id: str, target_ip: str, probe_type: ProbeType
    ) -> ProbeResultSchema:
        raise NotImplementedError("GNS3 probe execution requires node console command support")

    async def _request(self, method: str, path: str, timeout: float = 15.0, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(
                auth=(self.user, self.password), timeout=timeout
            ) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GNS3AdapterError(f"GNS3 request failed: {method} {url}: {exc}") from exc

        if not response.content:
            return {}
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise GNS3AdapterError(f"GNS3 returned invalid JSON for {method} {url}") from exc

    def _ensure_templates_available(self, plan) -> None:
        missing_kinds = sorted({
            node.engineKind
            for node in plan.nodes
            if node.engineKind in {"network-device", "host", "cloud"}
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
            "properties": {
                "octet_node_id": node.id,
                "octet_base_type": node.baseType,
                "octet_role": node.role,
            },
        }

    @staticmethod
    def _build_link_payload(
        link: EngineLinkPlanSchema,
        node_id_map: Mapping[str, str],
    ) -> dict:
        try:
            source_gns3_id = node_id_map[link.sourceNodeId]
            target_gns3_id = node_id_map[link.targetNodeId]
        except KeyError as exc:
            raise GNS3AdapterError(
                f"Cannot build GNS3 link payload for '{link.id}': missing node mapping for {exc.args[0]}"
            ) from exc

        return {
            "nodes": [
                {
                    "node_id": source_gns3_id,
                    "adapter_number": 0,
                    "port_number": 0,
                    "label": {
                        "text": link.sourcePort,
                    },
                },
                {
                    "node_id": target_gns3_id,
                    "adapter_number": 0,
                    "port_number": 0,
                    "label": {
                        "text": link.targetPort,
                    },
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
