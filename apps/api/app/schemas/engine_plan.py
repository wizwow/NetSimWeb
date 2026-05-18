from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.topology import LinkType, NodeBaseType, Protocol, VendorType


EngineKind = Literal["network-device", "host", "cloud", "site"]


class EngineInterfacePlanSchema(BaseModel):
    nodeId: str
    port: str
    peerNodeId: str
    peerPort: str
    linkId: str
    ip: Optional[str] = None
    subnet: Optional[str] = None


class EngineNodePlanSchema(BaseModel):
    id: str
    label: str
    baseType: NodeBaseType
    engineKind: EngineKind
    role: Optional[str] = None
    protocols: List[Protocol] = Field(default_factory=list)
    loopback: Optional[str] = None
    vendor: Optional[VendorType] = None
    platform: Optional[str] = None
    imageRef: Optional[str] = None
    interfaces: List[EngineInterfacePlanSchema] = Field(default_factory=list)


class EngineLinkPlanSchema(BaseModel):
    id: str
    sourceNodeId: str
    sourcePort: str
    targetNodeId: str
    targetPort: str
    linkType: LinkType
    subnet: Optional[str] = None
    sourceIp: Optional[str] = None
    targetIp: Optional[str] = None
    qos: Optional[Dict[str, Any]] = None
    faultState: Optional[Dict[str, Any]] = None


class EngineDeploymentPlanSchema(BaseModel):
    name: str
    abstractionLevel: str = "logical"
    nodeCount: int
    linkCount: int
    nodes: List[EngineNodePlanSchema] = Field(default_factory=list)
    links: List[EngineLinkPlanSchema] = Field(default_factory=list)
