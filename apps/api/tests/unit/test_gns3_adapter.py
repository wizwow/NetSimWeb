import pytest
import httpx

from app.engines.gns3 import GNS3AdapterError, GNS3SimulationEngine
from app.schemas.topology import NetworkNodeSchema, TopologyBase
from app.services.topology_translator import translate_topology_to_engine_plan
from app.services.templates import TemplateService


pytestmark = pytest.mark.anyio


class MockAsyncClient:
    requests = []
    response_queue = []
    captured_auth = None
    captured_timeout = None

    def __init__(self, auth=None, timeout=None):
        self.__class__.captured_auth = auth
        self.__class__.captured_timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def request(self, method, url, **kwargs):
        self.__class__.requests.append((method, url, kwargs))
        next_response = self.__class__.response_queue.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return next_response


def reset_mock_client():
    MockAsyncClient.requests = []
    MockAsyncClient.response_queue = []
    MockAsyncClient.captured_auth = None
    MockAsyncClient.captured_timeout = None


def response(status_code=200, payload=None):
    request = httpx.Request("POST", "http://gns3.local")
    return httpx.Response(status_code, json=payload or {}, request=request)


@pytest.fixture(autouse=True)
def patch_httpx(monkeypatch):
    reset_mock_client()
    monkeypatch.setattr("app.engines.gns3.httpx.AsyncClient", MockAsyncClient)


async def test_create_blank_topology_posts_project_to_configured_gns3_url():
    MockAsyncClient.response_queue = [response(payload={"project_id": "project-1"})]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local/",
        user="admin",
        password="secret",
    )

    project_id = await engine.create_topology(TemplateService().instantiate("blank"))

    assert project_id == "project-1"
    assert MockAsyncClient.captured_auth == ("admin", "secret")
    assert MockAsyncClient.captured_timeout == 15.0
    assert MockAsyncClient.requests == [
        ("POST", "http://gns3.local/v2/projects", {"json": {"name": "Blank"}})
    ]


async def test_create_topology_uses_translated_plan_and_requires_template_mappings():
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    with pytest.raises(GNS3AdapterError, match="template mappings"):
        await engine.create_topology(TemplateService().instantiate("ospf-3-sites"))

    assert MockAsyncClient.requests == []


async def test_create_topology_allows_configured_template_mapping():
    MockAsyncClient.response_queue = [response(payload={"project_id": "project-2"})]
    topology = TopologyBase(
        name="Router Only",
        nodes=[
            NetworkNodeSchema(
                id="r1",
                label="R1",
                position={"x": 0, "y": 0},
                baseType="router",
                tags=[],
            )
        ],
        edges=[],
    )
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
        template_mappings={"network-device": "tpl-router"},
    )

    project_id = await engine.create_topology(topology)

    assert project_id == "project-2"
    assert MockAsyncClient.requests[0][1] == "http://gns3.local/v2/projects"


async def test_template_resolution_and_future_node_payload_are_deterministic():
    topology = TopologyBase(
        name="Router Only",
        nodes=[
            NetworkNodeSchema(
                id="r1",
                label="R1",
                position={"x": 0, "y": 0},
                baseType="router",
                role="edge",
                tags=[],
            )
        ],
        edges=[],
    )
    plan = translate_topology_to_engine_plan(topology)
    node = plan.nodes[0]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
        template_mappings={"network-device": "tpl-router"},
    )

    assert engine._resolve_template_id(node) == "tpl-router"
    assert engine._build_node_payload(node) == {
        "name": "R1",
        "template_id": "tpl-router",
        "x": 0,
        "y": 0,
        "compute_id": "local",
        "properties": {
            "netsimflow_node_id": "r1",
            "netsimflow_base_type": "router",
            "netsimflow_role": "edge",
        },
    }


async def test_missing_template_mapping_for_payload_helper_is_actionable():
    topology = TopologyBase(
        name="Host Only",
        nodes=[
            NetworkNodeSchema(
                id="h1",
                label="Host 1",
                position={"x": 0, "y": 0},
                baseType="host",
                tags=[],
            )
        ],
        edges=[],
    )
    plan = translate_topology_to_engine_plan(topology)
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
        template_mappings={"network-device": "tpl-router"},
    )

    with pytest.raises(GNS3AdapterError, match="host"):
        engine._build_node_payload(plan.nodes[0])


async def test_future_link_payload_uses_node_id_mapping_and_fault_state():
    topology = TemplateService().instantiate("ospf-3-sites")
    plan = translate_topology_to_engine_plan(topology)
    link = next(item for item in plan.links if item.id == "link-branch-a-branch-b")
    link.faultState = {"active": True, "type": "link-down"}

    payload = GNS3SimulationEngine._build_link_payload(
        link,
        {
            link.sourceNodeId: "gns3-source",
            link.targetNodeId: "gns3-target",
        },
    )

    assert payload["nodes"][0]["node_id"] == "gns3-source"
    assert payload["nodes"][0]["label"]["text"] == link.sourcePort
    assert payload["nodes"][1]["node_id"] == "gns3-target"
    assert payload["nodes"][1]["label"]["text"] == link.targetPort
    assert payload["suspend"] is True


async def test_future_link_payload_requires_complete_node_id_mapping():
    topology = TemplateService().instantiate("ospf-3-sites")
    plan = translate_topology_to_engine_plan(topology)
    link = plan.links[0]

    with pytest.raises(GNS3AdapterError, match="missing node mapping"):
        GNS3SimulationEngine._build_link_payload(link, {})


async def test_start_and_stop_call_project_lifecycle_endpoints():
    MockAsyncClient.response_queue = [response(), response()]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    await engine.start_topology("project-1")
    await engine.stop_topology("project-1")

    assert MockAsyncClient.requests == [
        ("POST", "http://gns3.local/v2/projects/project-1/open", {}),
        ("POST", "http://gns3.local/v2/projects/project-1/close", {}),
    ]


async def test_gns3_status_strings_map_to_node_status():
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    assert await engine.get_node_status("node:started") == "running"
    assert await engine.get_node_status("node:running") == "running"
    assert await engine.get_node_status("node:starting") == "booting"
    assert await engine.get_node_status("node:suspended") == "degraded"
    assert await engine.get_node_status("node:stopped") == "stopped"
    assert await engine.get_node_status("node:unknown") == "error"


async def test_http_errors_become_adapter_errors():
    MockAsyncClient.response_queue = [
        httpx.ConnectError("connection refused", request=httpx.Request("POST", "http://gns3.local"))
    ]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    with pytest.raises(GNS3AdapterError, match="GNS3 request failed"):
        await engine.start_topology("project-1")


async def test_missing_project_id_raises_adapter_error():
    MockAsyncClient.response_queue = [response(payload={"name": "missing id"})]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    with pytest.raises(GNS3AdapterError, match="project id"):
        await engine.create_topology(TemplateService().instantiate("blank"))


async def test_fault_and_probe_are_explicitly_unsupported_for_now():
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    with pytest.raises(NotImplementedError, match="fault injection"):
        await engine.inject_fault("link-1", "link-down")

    with pytest.raises(NotImplementedError, match="probe execution"):
        await engine.run_probe("r1", "10.0.1.2", "ping")
