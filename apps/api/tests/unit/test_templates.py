from app.services.templates import TemplateService


def test_list_templates_includes_expected_defaults():
    templates = TemplateService().list_templates()
    template_ids = {template.id for template in templates}

    assert {"blank", "hub-spoke", "ospf-3-sites"}.issubset(template_ids)


def test_instantiate_ospf_template_applies_autoip():
    topology = TemplateService().instantiate("ospf-3-sites")

    assert topology.name == "OSPF 3 Sites"
    assert len(topology.nodes) == 4
    assert len(topology.edges) == 4
    assert all(edge.ipConfig and edge.ipConfig.get("subnet") for edge in topology.edges)

    routers = [node for node in topology.nodes if node.baseType == "router"]
    # Loopbacks are no longer auto-assigned
