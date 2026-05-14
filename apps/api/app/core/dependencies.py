from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.engines.base import SimulationEngineInterface
from app.engines.mock import MockSimulationEngine

# Inizializziamo il mock engine come singleton per ora
_mock_engine_instance = MockSimulationEngine()

def get_simulation_engine() -> SimulationEngineInterface:
    """Dependency che inietta il motore di simulazione corrente (Mock o GNS3 in futuro)."""
    return _mock_engine_instance
