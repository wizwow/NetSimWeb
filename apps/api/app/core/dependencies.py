import os

from app.engines.base import SimulationEngineInterface
from app.engines.mock import MockSimulationEngine

_engine_instance: SimulationEngineInterface | None = None


def get_simulation_engine() -> SimulationEngineInterface:
    """Return the active simulation engine based on ``SIMULATION_ENGINE`` env var."""
    global _engine_instance
    if _engine_instance is not None:
        return _engine_instance

    engine_type = os.getenv("SIMULATION_ENGINE", "mock").lower()

    if engine_type == "gns3":
        from app.engines.gns3 import GNS3SimulationEngine

        _engine_instance = GNS3SimulationEngine(
            base_url=os.getenv("GNS3_URL", "http://localhost:3080"),
            user=os.getenv("GNS3_USER", "admin"),
            password=os.getenv("GNS3_PASSWORD", "admin"),
        )
    else:
        _engine_instance = MockSimulationEngine()

    return _engine_instance
