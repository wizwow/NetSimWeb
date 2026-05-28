import pytest

from app.schemas.topology import (
    NetworkLinkSchema,
    NetworkNodeSchema,
    TopologyBase,
    TopologyImportSchema,
)
from app.services.templates import TemplateService
from app.services.topology_translator import (
    TopologyTranslationError,
    translate_topology_to_engine_plan,
)


def test_blank_template_translates_to_empty_plan():
    topology = TemplateService().instantiate("blank")

    plan = translate_topology_to_engine_plan(topology)

    assert plan.name == "Blank"
    assert plan.nodeCount == 0
    assert plan.linkCount == 0
    assert plan.nodes == []
    assert plan.links == []


def test_hub_spoke_template_translates_nodes_links_and_interfaces():
    topology = TemplateService().instantiate("hub-spoke")

    plan = translate_topology_to_engine_plan(topology)

    assert plan.nodeCount == 5
    assert plan.linkCount == 4

    hub = next(node for node in plan.nodes if node.id == "hub-r1")
    host = next(node for node in plan.nodes if node.id == "host-a")

    assert hub.engineKind == "network-device"
    assert hub.role == "hub"
    assert hub.protocols == ["ospf"]
    assert [interface.port for interface in hub.interfaces] == ["eth0", "eth1"]

    assert host.engineKind == "host"
    assert len(host.interfaces) == 1
    assert host.interfaces[0].peerNodeId == "branch-a-r1"


def test_ospf_template_preserves_ips_qos_and_cloud_link():
    topology = TemplateService().instantiate("ospf-3-sites")

    plan = translate_topology_to_engine_plan(topology)

    hq = next(node for node in plan.nodes if node.id == "site-hq")
    cloud = next(node for node in plan.nodes if node.id == "cloud-internet")
    branch_link = next(link for link in plan.links if link.id == "link-branch-a-branch-b")
    internet_link = next(link for link in plan.links if link.id == "link-hq-internet")

    assert hq.protocols == ["ospf"]
    assert len(hq.interfaces) == 3
    assert branch_link.subnet == "10.0.1.0/30"
    assert branch_link.sourceIp == "10.0.1.1"
    assert branch_link.targetIp == "10.0.1.2"
    assert branch_link.qos == {
        "bandwidthMbps": 100.0,
        "latencyMs": 15.0,
        "packetLossPercent": None,
    }
    assert cloud.engineKind == "cloud"
    assert internet_link.targetNodeId == "cloud-internet"


def test_translation_is_deterministic_for_same_input():
    topology = TemplateService().instantiate("ospf-3-sites")

    first = translate_topology_to_engine_plan(topology)
    second = translate_topology_to_engine_plan(topology)

    assert first.model_dump() == second.model_dump()


def test_imported_netsimflow_json_topology_translates():
    import_data = TopologyImportSchema(
        exportFormat="netsimflow-v1",
        name="Imported",
        abstractionLevel="logical",
        status="draft",
        nodes=[
            NetworkNodeSchema(
                id="r1",
                label="R1",
                position={"x": 0, "y": 0},
                baseType="router",
                tags=[],
            ),
            NetworkNodeSchema(
                id="r2",
                label="R2",
                position={"x": 100, "y": 0},
                baseType="router",
                tags=[],
            ),
        ],
        edges=[
            NetworkLinkSchema(
                id="link-r1-r2",
                sourceNodeId="r1",
                sourcePort="eth0",
                targetNodeId="r2",
                targetPort="eth0",
                linkType="ethernet",
                ipConfig={
                    "subnet": "10.10.0.0/30",
                    "sourceIp": "10.10.0.1",
                    "targetIp": "10.10.0.2",
                },
            )
        ],
    )
    topology = TopologyBase(
        name=import_data.name,
        abstractionLevel=import_data.abstractionLevel,
        status=import_data.status,
        nodes=import_data.nodes,
        edges=import_data.edges,
    )

    plan = translate_topology_to_engine_plan(topology)

    assert plan.name == "Imported"
    assert plan.links[0].subnet == "10.10.0.0/30"
    assert plan.nodes[0].interfaces[0].ip == "10.10.0.1"


def test_missing_link_endpoint_raises_translation_error():
    topology = TopologyBase(
        name="Broken",
        nodes=[
            NetworkNodeSchema(
                id="r1",
                label="R1",
                position={"x": 0, "y": 0},
                baseType="router",
                tags=[],
            )
        ],
        edges=[
            NetworkLinkSchema(
                id="link-missing",
                sourceNodeId="r1",
                sourcePort="eth0",
                targetNodeId="r2",
                targetPort="eth0",
                linkType="ethernet",
            )
        ],
    )

    with pytest.raises(TopologyTranslationError, match="missing target node 'r2'"):
        translate_topology_to_engine_plan(topology)


@pytest.mark.parametrize("link_type", ["logical", "vpn-tunnel"])
def test_unsupported_link_type_raises_translation_error(link_type):
    topology = TopologyBase(
        name="Unsupported",
        nodes=[
            NetworkNodeSchema(
                id="r1",
                label="R1",
                position={"x": 0, "y": 0},
                baseType="router",
                tags=[],
            ),
            NetworkNodeSchema(
                id="r2",
                label="R2",
                position={"x": 100, "y": 0},
                baseType="router",
                tags=[],
            ),
        ],
        edges=[
            NetworkLinkSchema(
                id="link-unsupported",
                sourceNodeId="r1",
                sourcePort="eth0",
                targetNodeId="r2",
                targetPort="eth0",
                linkType=link_type,
            )
        ],
    )

    with pytest.raises(TopologyTranslationError, match=f"Unsupported link type '{link_type}'"):
        translate_topology_to_engine_plan(topology)
