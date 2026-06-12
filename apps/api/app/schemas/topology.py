from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from app.schemas.engine_plan import GNS3MappingsSchema

# ── Mirrors packages/shared-types/src/topology.ts ──

NodeBaseType = Literal["router", "switch", "firewall", "cloud", "host", "site"]
NodeStatus = Literal["stopped", "booting", "running", "error", "degraded"]
VendorType = Literal["cisco", "juniper", "arista", "mikrotik", "generic"]
Protocol = Literal["ospf", "bgp", "eigrp", "static", "rip"]
LinkType = Literal["ethernet", "serial", "fiber", "vpn-tunnel", "logical"]
FaultType = Literal["link-down", "high-latency", "packet-loss"]
ProbeType = Literal["ping", "traceroute"]


class LogicalInterfaceSchema(BaseModel):
    name: str
    ip: Optional[str] = None
    subnet: Optional[str] = None
    mac: Optional[str] = None
    status: Literal["up", "down"] = "up"


class RoutingConfigSchema(BaseModel):
    model_config = {"extra": "allow"}
    processId: Optional[int] = None
    area: Optional[int] = None
    routerId: Optional[str] = None


class LogicalConfigSchema(BaseModel):
    interfaces: List[LogicalInterfaceSchema] = []
    routingConfig: Optional[RoutingConfigSchema] = None
    loopback: Optional[str] = None


class VendorSpecSchema(BaseModel):
    vendor: VendorType
    platform: str
    imageRef: Optional[str] = None
    cliConfig: Optional[str] = None
    features: Optional[Dict[str, Any]] = None


class RuntimeStateSchema(BaseModel):
    status: NodeStatus = "stopped"
    cpuPercent: Optional[float] = None
    memMB: Optional[float] = None
    nodeId: Optional[str] = None


class IPConfigSchema(BaseModel):
    subnet: str
    sourceIp: Optional[str] = None
    targetIp: Optional[str] = None


class QoSSchema(BaseModel):
    bandwidthMbps: Optional[float] = None
    latencyMs: Optional[float] = None
    packetLossPercent: Optional[float] = None


class FaultStateSchema(BaseModel):
    active: bool
    type: Optional[FaultType] = None
    triggeredAt: Optional[str] = None


class ProbeResultSchema(BaseModel):
    success: bool
    output: str
    rttMs: Optional[float] = None
    hops: Optional[List[Dict[str, Any]]] = None


class ProbeRequestSchema(BaseModel):
    sourceNodeId: str
    targetIp: str
    probeType: ProbeType = "ping"


class FaultRequestSchema(BaseModel):
    linkId: str
    faultType: FaultType


# ── Node / Link ──

class NetworkNodeSchema(BaseModel):
    id: str
    label: str
    position: Dict[str, float]
    baseType: NodeBaseType
    role: Optional[Literal["core", "distribution", "access", "edge", "hub", "spoke"]] = None
    protocols: Optional[List[Protocol]] = None
    logicalConfig: Optional[Dict[str, Any]] = None
    vendorSpec: Optional[VendorSpecSchema] = None
    runtimeState: Optional[RuntimeStateSchema] = None
    tags: List[str] = []


class NetworkLinkSchema(BaseModel):
    id: str
    sourceNodeId: str
    sourcePort: str
    targetNodeId: str
    targetPort: str
    linkType: LinkType
    ipConfig: Optional[Dict[str, Any]] = None
    qos: Optional[QoSSchema] = None
    faultState: Optional[FaultStateSchema] = None


# ── Topology request / response ──

class TopologyBase(BaseModel):
    name: str
    description: Optional[str] = None
    abstraction_level: str = Field(default="logical", alias="abstractionLevel")
    status: str = "draft"
    nodes: List[NetworkNodeSchema] = []
    edges: List[NetworkLinkSchema] = []

    model_config = {"populate_by_name": True}


class TopologyCreate(TopologyBase):
    pass


class TopologyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    abstraction_level: Optional[str] = Field(default=None, alias="abstractionLevel")
    status: Optional[str] = None
    nodes: Optional[List[NetworkNodeSchema]] = None
    edges: Optional[List[NetworkLinkSchema]] = None

    model_config = {"populate_by_name": True}


class TopologyRead(TopologyBase):
    id: uuid.UUID
    owner_id: Optional[uuid.UUID] = None
    engine_topo_id: Optional[str] = None
    gns3_mappings: Optional[GNS3MappingsSchema] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class TopologyExportSchema(BaseModel):
    exportFormat: Literal["octet-v1"] = "octet-v1"
    topologyId: Optional[uuid.UUID] = None
    name: str
    description: Optional[str] = None
    abstractionLevel: str = "logical"
    status: str = "draft"
    engineTopoId: Optional[str] = None
    exportedAt: Optional[str] = None
    nodes: List[NetworkNodeSchema] = Field(default_factory=list)
    edges: List[NetworkLinkSchema] = Field(default_factory=list)


class TopologyImportSchema(BaseModel):
    exportFormat: Literal["octet-v1"]
    name: str
    description: Optional[str] = None
    abstractionLevel: str = "logical"
    status: str = "draft"
    nodes: List[NetworkNodeSchema] = Field(default_factory=list)
    edges: List[NetworkLinkSchema] = Field(default_factory=list)


class TemplateSummarySchema(BaseModel):
    id: str
    name: str
    description: str
    tags: List[str] = []
    abstractionLevel: str = "logical"


class TemplateSchema(TemplateSummarySchema):
    nodes: List[NetworkNodeSchema] = []
    edges: List[NetworkLinkSchema] = []
    postProcessors: List[str] = []
