import os

from app.core.gns3_config import GNS3ConfigError, load_gns3_config
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

        try:
            config = load_gns3_config()
        except GNS3ConfigError as exc:
            raise RuntimeError(f"Invalid GNS3 configuration: {exc}") from exc

        _engine_instance = GNS3SimulationEngine(
            base_url=config.base_url,
            user=config.user,
            password=config.password,
            template_mappings=config.template_mappings,
        )
    else:
        _engine_instance = MockSimulationEngine()

    return _engine_instance
