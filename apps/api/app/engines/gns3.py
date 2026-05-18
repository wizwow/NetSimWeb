"""GNS3 simulation engine adapter.

All GNS3 HTTP interactions are encapsulated here.
No other module may call GNS3 directly (ARCHITECTURE.md §3.2).
"""

import json
from typing import Mapping

import httpx

from app.engines.base import SimulationEngineInterface
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
