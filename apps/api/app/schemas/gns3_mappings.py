"""Persisted engine-id mappings for a topology.

Lives in its own module (rather than ``engine_plan.py``) to break a
circular import: ``engine_plan.py`` imports the type literals
(``LinkType``, ``NodeBaseType``, ``Protocol``, ``VendorType``) from
``topology.py``, and ``topology.py`` needs ``GNS3MappingsSchema`` to
type the ``gns3_mappings`` field on ``TopologyRead``. Moving this
class out lets both modules import it without forming a cycle.
"""

from typing import Dict

from pydantic import BaseModel, Field


class GNS3MappingsSchema(BaseModel):
    """Persisted engine-id mappings for a topology.

    ``nodes`` maps an Octet ``NetworkNode.id`` to the engine-side
    identifier returned by the simulation engine (currently GNS3
    ``node_id``). ``links`` is populated by the link-provisioning slice
    (Phase 3) and is always present (possibly empty) so the response
    shape is stable.
    """

    nodes: Dict[str, str] = Field(default_factory=dict)
    links: Dict[str, str] = Field(default_factory=dict)
