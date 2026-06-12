import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.models.base import Base

class Topology(Base):
    __tablename__ = "topologies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    abstraction_level = Column(String, default="logical") # logical | vendor-specific
    engine_topo_id = Column(String, nullable=True)
    status = Column(String, default="draft") # draft | running | stopped | error
    graph_json = Column(JSONB, nullable=False, server_default='{}')
    gns3_mappings = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
