import pytest

from app.core.gns3_config import GNS3ConfigError, load_gns3_config, parse_template_mappings


def test_load_gns3_config_uses_defaults_and_parses_template_mappings():
    config = load_gns3_config(
        {
            "GNS3_URL": "http://gns3.local/",
            "GNS3_USER": "admin",
            "GNS3_PASSWORD": "secret",
            "GNS3_TEMPLATE_MAPPINGS": '{"network-device":"tpl-router","host":"tpl-host"}',
        }
    )

    assert config.base_url == "http://gns3.local"
    assert config.user == "admin"
    assert config.password == "secret"
    assert config.template_mappings == {
        "network-device": "tpl-router",
        "host": "tpl-host",
    }


def test_parse_template_mappings_rejects_invalid_json():
    with pytest.raises(GNS3ConfigError, match="valid JSON"):
        parse_template_mappings("{nope")


def test_parse_template_mappings_rejects_invalid_keys():
    with pytest.raises(GNS3ConfigError, match="Unsupported GNS3 template mapping keys"):
        parse_template_mappings('{"router":"tpl-router"}')


def test_parse_template_mappings_rejects_empty_template_ids():
    with pytest.raises(GNS3ConfigError, match="non-empty string"):
        parse_template_mappings('{"network-device":" "}')
