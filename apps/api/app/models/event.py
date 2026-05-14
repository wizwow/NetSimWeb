from sqlalchemy import Column, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.models.base import Base

class SimulationEvent(Base):
    __tablename__ = "simulation_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    topology_id = Column(UUID(as_uuid=True), ForeignKey("topologies.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
