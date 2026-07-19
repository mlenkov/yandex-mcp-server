import json
from pathlib import Path

import pytest


def test_direct_config_uses_post():
    config_path = Path("app/yandex_configs/direct.json")
    if not config_path.exists():
        pytest.skip("direct.json not found")

    config = json.loads(config_path.read_text())
    for resource_name, resource in config.get("resources", {}).items():
        assert resource.get("method") == "POST", \
            f"Resource {resource_name} should be POST (JSON-RPC), got {resource.get('method')}"
