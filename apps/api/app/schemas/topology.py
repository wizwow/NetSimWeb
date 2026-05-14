from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class NetworkNodeSchema(BaseModel):
    id: str
    label: str
    position: Dict[str, float]
    baseType: str
    role: Optional[str] = None
    protocols: Optional[List[str]] = None
    logicalConfig: Optional[Dict[str, Any]] = None
    vendorSpec: Optional[Dict[str, Any]] = None
    runtimeState: Optional[Dict[str, Any]] = None
    tags: List[str] = []

class NetworkLinkSchema(BaseModel):
    id: str
    sourceNodeId: str
    sourcePort: str
    targetNodeId: str
    targetPort: str
    linkType: str
    ipConfig: Optional[Dict[str, Any]] = None
    qos: Optional[Dict[str, Any]] = None
    faultState: Optional[Dict[str, Any]] = None

class TopologyBase(BaseModel):
    name: str
    description: Optional[str] = None
    abstraction_level: str = "logical"
    status: str = "draft"
    nodes: List[NetworkNodeSchema] = []
    edges: List[NetworkLinkSchema] = []

class TopologyCreate(TopologyBase):
    pass

class TopologyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    abstraction_level: Optional[str] = None
    status: Optional[str] = None
    nodes: Optional[List[NetworkNodeSchema]] = None
    edges: Optional[List[NetworkLinkSchema]] = None

class TopologyRead(TopologyBase):
    id: uuid.UUID
    owner_id: Optional[uuid.UUID] = None
    engine_topo_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
