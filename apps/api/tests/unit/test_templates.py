from app.services.templates import TemplateService


def test_list_templates_includes_expected_defaults():
    templates = TemplateService().list_templates()
    template_ids = {template.id for template in templates}

    assert {"blank", "hub-spoke", "ospf-3-sites"}.issubset(template_ids)


def test_instantiate_ospf_template_returns_correct_structure():
    topology = TemplateService().instantiate("ospf-3-sites")

    assert topology.name == "OSPF 3 Sites"
    assert len(topology.nodes) == 4
    assert len(topology.edges) == 4
    assert topology.status == "draft"
