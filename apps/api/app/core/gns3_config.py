import json
import os
from dataclasses import dataclass
from typing import Mapping


SUPPORTED_GNS3_TEMPLATE_KINDS = {"network-device", "host", "cloud"}


class GNS3ConfigError(ValueError):
    """Raised when GNS3 environment configuration is not usable."""


@dataclass(frozen=True)
class GNS3Config:
    base_url: str
    user: str
    password: str
    template_mappings: dict[str, str]


def load_gns3_config(env: Mapping[str, str] | None = None) -> GNS3Config:
    values = env or os.environ
    return GNS3Config(
        base_url=values.get("GNS3_URL", "http://localhost:3080").rstrip("/"),
        user=values.get("GNS3_USER", "admin"),
        password=values.get("GNS3_PASSWORD", "admin"),
        template_mappings=parse_template_mappings(values.get("GNS3_TEMPLATE_MAPPINGS", "{}")),
    )


def parse_template_mappings(raw_value: str | None) -> dict[str, str]:
    if not raw_value:
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise GNS3ConfigError(
            "GNS3_TEMPLATE_MAPPINGS must be valid JSON, for example "
            '\'{"network-device":"template-id","host":"template-id"}\''
        ) from exc

    if not isinstance(parsed, dict):
        raise GNS3ConfigError("GNS3_TEMPLATE_MAPPINGS must be a JSON object")

    invalid_keys = sorted(set(parsed) - SUPPORTED_GNS3_TEMPLATE_KINDS)
    if invalid_keys:
        allowed = ", ".join(sorted(SUPPORTED_GNS3_TEMPLATE_KINDS))
        invalid = ", ".join(invalid_keys)
        raise GNS3ConfigError(
            f"Unsupported GNS3 template mapping keys: {invalid}. Supported keys: {allowed}."
        )

    mappings: dict[str, str] = {}
    for key, value in parsed.items():
        if not isinstance(value, str) or not value.strip():
            raise GNS3ConfigError(f"GNS3 template mapping for '{key}' must be a non-empty string")
        mappings[key] = value.strip()
    return mappings
