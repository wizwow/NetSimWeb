"""Manual GNS3 readiness helper.

Run from apps/api:
    .\.venv\Scripts\python.exe scripts\gns3_readiness_check.py

This script does not touch the database and is not collected by pytest.
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.gns3_config import GNS3ConfigError, load_gns3_config  # noqa: E402


async def main() -> int:
    try:
        config = load_gns3_config()
    except GNS3ConfigError as exc:
        print(f"GNS3 configuration error: {exc}")
        return 2

    print(f"GNS3 URL: {config.base_url}")
    print(f"GNS3 user: {config.user}")
    print(f"Configured template mappings: {json.dumps(config.template_mappings, indent=2)}")

    try:
        async with httpx.AsyncClient(auth=(config.user, config.password), timeout=8.0) as client:
            version_response = await client.get(f"{config.base_url}/v2/version")
            version_response.raise_for_status()
            templates_response = await client.get(f"{config.base_url}/v2/templates")
            templates_response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"GNS3 server not reachable or not ready: {exc}")
        print("Keep SIMULATION_ENGINE=mock until a GNS3 server is reachable.")
        return 1

    print("GNS3 server reachable.")
    print(f"Version: {version_response.json()}")

    templates = templates_response.json()
    if not templates:
        print("No GNS3 templates returned. Create/import templates before live provisioning.")
        return 0

    print("\nAvailable templates:")
    for template in templates:
        template_id = template.get("template_id") or template.get("id")
        name = template.get("name", "<unnamed>")
        template_type = template.get("template_type") or template.get("type") or "unknown"
        print(f"- {name} ({template_type}): {template_id}")

    first_template_id = templates[0].get("template_id") or templates[0].get("id")
    if first_template_id:
        suggestion = {
            "network-device": first_template_id,
            "host": first_template_id,
            "cloud": first_template_id,
        }
        print("\nExample GNS3_TEMPLATE_MAPPINGS candidate:")
        print(json.dumps(suggestion, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
