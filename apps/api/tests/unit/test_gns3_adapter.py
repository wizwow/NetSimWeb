import pytest
import httpx

from app.engines.gns3 import GNS3AdapterError, GNS3SimulationEngine
from app.schemas.topology import NetworkLinkSchema, NetworkNodeSchema, TopologyBase
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

    result = await engine.create_topology(TemplateService().instantiate("blank"))

    assert result.engine_topology_id == "project-1"
    assert result.node_id_map == {}
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
    MockAsyncClient.response_queue = [
        response(payload={"project_id": "project-2"}),
        response(payload={"node_id": "gns3-r1"}),
    ]
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

    result = await engine.create_topology(topology)

    assert result.engine_topology_id == "project-2"
    assert result.node_id_map == {"r1": "gns3-r1"}
    assert MockAsyncClient.requests[0][1] == "http://gns3.local/v2/projects"
    assert MockAsyncClient.requests[1] == (
        "POST",
        "http://gns3.local/v2/projects/project-2/nodes",
        {
            "json": {
                "name": "R1",
                "template_id": "tpl-router",
                "x": 0,
                "y": 0,
                "compute_id": "local",
                "properties": {
                    "octet_node_id": "r1",
                    "octet_base_type": "router",
                    "octet_role": None,
                },
            }
        },
    )


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
            "octet_node_id": "r1",
            "octet_base_type": "router",
            "octet_role": "edge",
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


async def test_create_topology_provisions_each_node_and_returns_id_mapping():
    """A 4-node ospf-3-sites topology results in 1 project POST + 4 node POSTs + 4 link POSTs.

    The returned ``node_id_map`` and ``link_id_map`` must map every
    Octet node/link id to the engine-side id returned by GNS3, so the
    simulation service can persist it on the topology for later
    operations (status polls, fault injection, etc.).
    """
    MockAsyncClient.response_queue = [
        response(payload={"project_id": "project-ospf"}),
        response(payload={"node_id": "gns3-hq"}),
        response(payload={"node_id": "gns3-branch-a"}),
        response(payload={"node_id": "gns3-branch-b"}),
        response(payload={"node_id": "gns3-cloud"}),
        response(payload={"link_id": "gns3-link-1"}),
        response(payload={"link_id": "gns3-link-2"}),
        response(payload={"link_id": "gns3-link-3"}),
        response(payload={"link_id": "gns3-link-4"}),
    ]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
        template_mappings={
            "network-device": "tpl-router",
            "host": "tpl-host",
            "cloud": "tpl-cloud",
        },
    )

    result = await engine.create_topology(TemplateService().instantiate("ospf-3-sites"))

    assert result.engine_topology_id == "project-ospf"
    assert result.node_id_map == {
        "site-hq": "gns3-hq",
        "branch-a-r1": "gns3-branch-a",
        "branch-b-r1": "gns3-branch-b",
        "cloud-internet": "gns3-cloud",
    }
    assert result.link_id_map == {
        "link-hq-branch-a": "gns3-link-1",
        "link-hq-branch-b": "gns3-link-2",
        "link-branch-a-branch-b": "gns3-link-3",
        "link-hq-internet": "gns3-link-4",
    }
    # Verify each HTTP call was a POST to the expected endpoint.
    method_url_pairs = [(method, url) for method, url, _ in MockAsyncClient.requests]
    assert method_url_pairs == [
        ("POST", "http://gns3.local/v2/projects"),
        ("POST", "http://gns3.local/v2/projects/project-ospf/nodes"),
        ("POST", "http://gns3.local/v2/projects/project-ospf/nodes"),
        ("POST", "http://gns3.local/v2/projects/project-ospf/nodes"),
        ("POST", "http://gns3.local/v2/projects/project-ospf/nodes"),
        ("POST", "http://gns3.local/v2/projects/project-ospf/links"),
        ("POST", "http://gns3.local/v2/projects/project-ospf/links"),
        ("POST", "http://gns3.local/v2/projects/project-ospf/links"),
        ("POST", "http://gns3.local/v2/projects/project-ospf/links"),
    ]
    # Verify the first node payload uses the correct template and metadata.
    first_node_payload = MockAsyncClient.requests[1][2]["json"]
    assert first_node_payload["name"] in {"HQ", "Branch A", "Branch B", "Cloud Internet"}
    assert first_node_payload["template_id"] in {"tpl-router", "tpl-host", "tpl-cloud"}
    assert "octet_node_id" in first_node_payload["properties"]


async def test_create_topology_cleans_up_project_when_a_node_post_fails():
    """If a node POST fails, the half-provisioned GNS3 project is deleted
    and the original error is re-raised so the next start does not see
    stale orphan nodes.
    """
    MockAsyncClient.response_queue = [
        response(payload={"project_id": "project-cleanup"}),
        response(payload={"node_id": "gns3-hq"}),
        # Third call (second node POST) returns a 500 from GNS3.
        response(status_code=500, payload={"message": "internal error"}),
        # Project DELETE that should follow as cleanup — the response is
        # consumed but its result is irrelevant; we only assert it was
        # called and the error is the original node-creation error.
        response(),
    ]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
        template_mappings={
            "network-device": "tpl-router",
            "host": "tpl-host",
            "cloud": "tpl-cloud",
        },
    )

    with pytest.raises(GNS3AdapterError, match="GNS3 request failed"):
        await engine.create_topology(TemplateService().instantiate("ospf-3-sites"))

    method_url_pairs = [(method, url) for method, url, _ in MockAsyncClient.requests]
    # No partial-result leak: the cleanup DELETE is the last call, and
    # the project id in the URL matches the one we tried to populate.
    assert method_url_pairs[-1] == ("DELETE", "http://gns3.local/v2/projects/project-cleanup")


async def test_create_topology_reports_missing_node_id_after_partial_success():
    """If GNS3 returns a node payload without ``node_id`` after a successful
    project creation, the adapter raises and cleans up the project.
    """
    MockAsyncClient.response_queue = [
        response(payload={"project_id": "project-bad-node"}),
        response(payload={"name": "no id"}),  # missing node_id
        response(),  # cleanup DELETE
    ]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
        template_mappings={"network-device": "tpl-router"},
    )

    with pytest.raises(GNS3AdapterError, match="did not include a node id"):
        await engine.create_topology(
            TopologyBase(
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
        )

    method_url_pairs = [(method, url) for method, url, _ in MockAsyncClient.requests]
    assert method_url_pairs[-1] == ("DELETE", "http://gns3.local/v2/projects/project-bad-node")


async def test_create_topology_provisions_links_with_resolved_node_endpoints():
    """A 2-router, 1-link topology results in 1 project POST + 2 node POSTs
    + 1 link POST. The link payload must translate both endpoints from
    the Octet node id to the GNS3 node id returned at node-provision
    time, and propagate the source/target port labels so the operator
    can identify the interfaces in the GNS3 UI.
    """
    MockAsyncClient.response_queue = [
        response(payload={"project_id": "project-2r1l"}),
        response(payload={"node_id": "gns3-r1"}),
        response(payload={"node_id": "gns3-r2"}),
        response(payload={"link_id": "gns3-link-1"}),
    ]
    topology = TopologyBase(
        name="Two Routers One Link",
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
                position={"x": 0, "y": 0},
                baseType="router",
                tags=[],
            ),
        ],
        edges=[
            NetworkLinkSchema(
                id="link-1",
                sourceNodeId="r1",
                sourcePort="eth0",
                targetNodeId="r2",
                targetPort="eth1",
                linkType="ethernet",
            )
        ],
    )
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
        template_mappings={"network-device": "tpl-router"},
    )

    result = await engine.create_topology(topology)

    assert result.engine_topology_id == "project-2r1l"
    assert result.node_id_map == {"r1": "gns3-r1", "r2": "gns3-r2"}
    assert result.link_id_map == {"link-1": "gns3-link-1"}
    # The link POST must be the final call, and its payload must use
    # the GNS3 node ids (not the Octet ones) for both endpoints.
    last_method, last_url, last_kwargs = MockAsyncClient.requests[-1]
    assert last_method == "POST"
    assert last_url == "http://gns3.local/v2/projects/project-2r1l/links"
    link_payload = last_kwargs["json"]
    assert link_payload["nodes"][0]["node_id"] == "gns3-r1"
    assert link_payload["nodes"][0]["label"]["text"] == "eth0"
    assert link_payload["nodes"][1]["node_id"] == "gns3-r2"
    assert link_payload["nodes"][1]["label"]["text"] == "eth1"
    assert link_payload["suspend"] is False


async def test_create_topology_cleans_up_project_when_a_link_post_fails():
    """If a link POST fails after all nodes have been provisioned, the
    half-provisioned GNS3 project is deleted and the original error
    is re-raised. The next start must not see a project that is missing
    links the canvas still claims exist.
    """
    MockAsyncClient.response_queue = [
        response(payload={"project_id": "project-link-fail"}),
        response(payload={"node_id": "gns3-r1"}),
        response(payload={"node_id": "gns3-r2"}),
        # Fourth call (first link POST) returns a 500 from GNS3.
        response(status_code=500, payload={"message": "link failure"}),
        # Project DELETE cleanup — the response is consumed but its
        # result is irrelevant; we only assert it was called and the
        # error is the original link-creation error.
        response(),
    ]
    topology = TopologyBase(
        name="Two Routers One Link",
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
                position={"x": 0, "y": 0},
                baseType="router",
                tags=[],
            ),
        ],
        edges=[
            NetworkLinkSchema(
                id="link-1",
                sourceNodeId="r1",
                sourcePort="eth0",
                targetNodeId="r2",
                targetPort="eth0",
                linkType="ethernet",
            )
        ],
    )
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
        template_mappings={"network-device": "tpl-router"},
    )

    with pytest.raises(GNS3AdapterError, match="GNS3 request failed"):
        await engine.create_topology(topology)

    method_url_pairs = [(method, url) for method, url, _ in MockAsyncClient.requests]
    # Cleanup DELETE is the last call, and the project id in the URL
    # matches the one we tried to populate.
    assert method_url_pairs[-1] == (
        "DELETE",
        "http://gns3.local/v2/projects/project-link-fail",
    )


async def test_create_topology_reports_missing_link_id_after_partial_success():
    """If GNS3 returns a link payload without ``link_id`` after a
    successful project + nodes + link POST, the adapter raises and
    cleans up the project.
    """
    MockAsyncClient.response_queue = [
        response(payload={"project_id": "project-bad-link"}),
        response(payload={"node_id": "gns3-r1"}),
        response(payload={"node_id": "gns3-r2"}),
        response(payload={"name": "no id"}),  # missing link_id
        response(),  # cleanup DELETE
    ]
    topology = TopologyBase(
        name="Two Routers One Link",
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
                position={"x": 0, "y": 0},
                baseType="router",
                tags=[],
            ),
        ],
        edges=[
            NetworkLinkSchema(
                id="link-1",
                sourceNodeId="r1",
                sourcePort="eth0",
                targetNodeId="r2",
                targetPort="eth0",
                linkType="ethernet",
            )
        ],
    )
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
        template_mappings={"network-device": "tpl-router"},
    )

    with pytest.raises(GNS3AdapterError, match="did not include a link id"):
        await engine.create_topology(topology)

    method_url_pairs = [(method, url) for method, url, _ in MockAsyncClient.requests]
    assert method_url_pairs[-1] == (
        "DELETE",
        "http://gns3.local/v2/projects/project-bad-link",
    )


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
