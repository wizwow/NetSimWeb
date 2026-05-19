"""GNS3 simulation engine adapter.

All GNS3 HTTP interactions are encapsulated here.
No other module may call GNS3 directly (ARCHITECTURE.md §3.2).
"""

import json
from typing import Mapping

import httpx

from app.engines.base import SimulationEngineInterface
from app.schemas.engine_plan import EngineLinkPlanSchema, EngineNodePlanSchema
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

    async def create_topology(self, topology: TopologyBase) -> str:
        plan = translate_topology_to_engine_plan(topology)
        self._ensure_templates_available(plan)

        payload = {"name": plan.name}
        project = await self._request("POST", "/v2/projects", json=payload)
        project_id = project.get("project_id") or project.get("projectId") or project.get("id")
        if not project_id:
            raise GNS3AdapterError("GNS3 project creation response did not include a project id")

        return str(project_id)

    async def start_topology(self, engine_topology_id: str) -> None:
        await self._request("POST", f"/v2/projects/{engine_topology_id}/open")

    async def stop_topology(self, engine_topology_id: str) -> None:
        await self._request("POST", f"/v2/projects/{engine_topology_id}/close")

    async def get_node_status(self, engine_node_id: str) -> NodeStatus:
        status = engine_node_id.rsplit(":", 1)[-1].lower()
        return self._map_node_status(status)

    async def inject_fault(self, engine_link_id: str, fault: FaultType) -> None:
        raise NotImplementedError("GNS3 fault injection requires link suspend mapping")

    async def run_probe(
        self, source_node_id: str, target_ip: str, probe_type: ProbeType
    ) -> ProbeResultSchema:
        raise NotImplementedError("GNS3 probe execution requires node console command support")

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(auth=(self.user, self.password), timeout=15.0) as client:
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
                "netsimflow_node_id": node.id,
                "netsimflow_base_type": node.baseType,
                "netsimflow_role": node.role,
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
