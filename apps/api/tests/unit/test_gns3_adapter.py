import pytest
import httpx
import asyncio

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
    # Blank topology has no nodes/links, so only the project POST is expected
    MockAsyncClient.response_queue = [
        response(payload=[]),  # templates
        response(payload={"project_id": "project-1"}),  # project
    ]
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
        ("GET", "http://gns3.local/v2/templates", {}),
        ("POST", "http://gns3.local/v2/projects", {"json": {"name": "Blank"}}),
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


async def test_create_topology_provisions_nodes_and_links():
    """create_topology should POST project, then each node, then each link."""
    MockAsyncClient.response_queue = [
        response(payload=[
            {"template_id": "tpl-router", "template_type": "qemu"}
        ]),  # templates
        response(payload={"project_id": "project-2"}),  # project
        response(payload={"node_id": "gns3-r1"}),        # node r1
        response(payload={"node_id": "gns3-r2"}),        # node r2
        response(payload={"link_id": "gns3-link-1"}),    # link
    ]
    topology = TopologyBase(
        name="Two Routers",
        nodes=[
            NetworkNodeSchema(
                id="r1", label="R1", position={"x": 0, "y": 0},
                baseType="router", tags=[],
            ),
            NetworkNodeSchema(
                id="r2", label="R2", position={"x": 100, "y": 0},
                baseType="router", tags=[],
            ),
        ],
        edges=[
            {
                "id": "link-1", "sourceNodeId": "r1", "sourcePort": "eth0",
                "targetNodeId": "r2", "targetPort": "eth0", "linkType": "ethernet",
            },
        ],
    )
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
        template_mappings={"network-device": "tpl-router"},
    )

    project_id = await engine.create_topology(topology)

    assert project_id == "project-2"
    assert len(MockAsyncClient.requests) == 5
    # templates query
    assert MockAsyncClient.requests[0][1] == "http://gns3.local/v2/templates"
    # project creation
    assert MockAsyncClient.requests[1][1] == "http://gns3.local/v2/projects"
    # node creation
    assert MockAsyncClient.requests[2][1] == "http://gns3.local/v2/projects/project-2/nodes"
    assert MockAsyncClient.requests[2][2]["json"]["node_type"] == "qemu"
    assert MockAsyncClient.requests[3][1] == "http://gns3.local/v2/projects/project-2/nodes"
    assert MockAsyncClient.requests[3][2]["json"]["node_type"] == "qemu"
    # link creation
    assert MockAsyncClient.requests[4][1] == "http://gns3.local/v2/projects/project-2/links"
    # registries populated
    assert "r1" in engine._node_registry
    assert "r2" in engine._node_registry
    assert "link-1" in engine._link_registry



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
        ("POST", "http://gns3.local/v2/projects/project-1/nodes/start", {}),
        ("POST", "http://gns3.local/v2/projects/project-1/nodes/stop", {}),
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
    MockAsyncClient.response_queue = [
        response(payload=[]),  # templates
        response(payload={"name": "missing id"}),  # project
    ]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    with pytest.raises(GNS3AdapterError, match="project id"):
        await engine.create_topology(TemplateService().instantiate("blank"))



async def test_inject_fault_link_down_sends_suspend():
    MockAsyncClient.response_queue = [response()]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )
    from app.engines.gns3 import _LinkEntry
    engine._link_registry["link-1"] = _LinkEntry("proj-1", "gns3-link-1")

    await engine.inject_fault("link-1", "link-down")

    assert MockAsyncClient.requests == [
        ("PUT", "http://gns3.local/v2/projects/proj-1/links/gns3-link-1",
         {"json": {"suspend": True}}),
    ]


async def test_inject_fault_high_latency_sends_filter():
    MockAsyncClient.response_queue = [response()]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )
    from app.engines.gns3 import _LinkEntry
    engine._link_registry["link-1"] = _LinkEntry("proj-1", "gns3-link-1")

    await engine.inject_fault("link-1", "high-latency")

    assert MockAsyncClient.requests[0][2] == {"json": {"filters": {"delay": [150]}}}


async def test_inject_fault_packet_loss_sends_filter():
    MockAsyncClient.response_queue = [response()]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )
    from app.engines.gns3 import _LinkEntry
    engine._link_registry["link-1"] = _LinkEntry("proj-1", "gns3-link-1")

    await engine.inject_fault("link-1", "packet-loss")

    assert MockAsyncClient.requests[0][2] == {"json": {"filters": {"packet_loss": [25]}}}


async def test_inject_fault_unknown_link_raises():
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    with pytest.raises(GNS3AdapterError, match="not found in GNS3 registry"):
        await engine.inject_fault("unknown-link", "link-down")


async def test_clear_fault_sends_unsuspend_and_empty_filters():
    MockAsyncClient.response_queue = [response()]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )
    from app.engines.gns3 import _LinkEntry
    engine._link_registry["link-1"] = _LinkEntry("proj-1", "gns3-link-1")

    await engine.clear_fault("link-1")

    assert MockAsyncClient.requests == [
        ("PUT", "http://gns3.local/v2/projects/proj-1/links/gns3-link-1",
         {"json": {"suspend": False, "filters": {}}}),
    ]


async def test_get_node_status_polls_gns3_when_registered():
    MockAsyncClient.response_queue = [
        response(payload={"status": "started", "node_id": "gns3-r1"}),
    ]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )
    from app.engines.gns3 import _NodeEntry
    engine._node_registry["r1"] = _NodeEntry("proj-1", "gns3-r1")

    status = await engine.get_node_status("r1")

    assert status == "running"
    assert MockAsyncClient.requests == [
        ("GET", "http://gns3.local/v2/projects/proj-1/nodes/gns3-r1", {}),
    ]


async def test_run_probe_unknown_node_raises():
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    with pytest.raises(GNS3AdapterError, match="not found in GNS3 registry"):
        await engine.run_probe("unknown-node", "10.0.1.1", "ping")


async def test_registry_export_and_reload_round_trips():
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )
    from app.engines.gns3 import _NodeEntry, _LinkEntry
    engine._node_registry["r1"] = _NodeEntry("proj-1", "gns3-r1")
    engine._link_registry["link-1"] = _LinkEntry("proj-1", "gns3-link-1")

    exported = engine.export_registries()

    engine2 = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )
    engine2.load_registries(exported)

    assert engine2._node_registry["r1"].gns3_node_id == "gns3-r1"
    assert engine2._link_registry["link-1"].gns3_link_id == "gns3-link-1"


async def test_parse_ping_output():
    raw = (
        "PING 10.0.1.2 (10.0.1.2) 56(84) bytes of data.\n"
        "64 bytes from 10.0.1.2: icmp_seq=1 ttl=64 time=1.23 ms\n"
        "--- 10.0.1.2 ping statistics ---\n"
        "1 packets transmitted, 1 received, 0% packet loss\n"
        "rtt min/avg/max/mdev = 1.23/1.23/1.23/0.000 ms"
    )
    result = GNS3SimulationEngine._parse_probe_output(raw, "ping")
    assert result.success is True
    assert result.rttMs == 1.23


async def test_parse_traceroute_output():
    raw = (
        "traceroute to 10.0.2.1 (10.0.2.1), 30 hops max\n"
        " 1  10.0.1.1  0.5 ms  0.4 ms  0.3 ms\n"
        " 2  10.0.2.1  1.2 ms  1.1 ms  1.0 ms\n"
    )
    result = GNS3SimulationEngine._parse_probe_output(raw, "traceroute")
    assert result.success is True
    assert len(result.hops) == 2
    assert result.hops[0]["ip"] == "10.0.1.1"
    assert result.hops[1]["ip"] == "10.0.2.1"


async def test_probe_command_vendor_specific():
    # Cisco
    cmd_cisco_ping = GNS3SimulationEngine._probe_command("10.0.1.2", "ping", vendor="cisco")
    cmd_cisco_trace = GNS3SimulationEngine._probe_command("10.0.1.2", "traceroute", vendor="cisco")
    assert cmd_cisco_ping == "ping 10.0.1.2 repeat 3"
    assert cmd_cisco_trace == "traceroute 10.0.1.2"

    # VPCS
    cmd_vpcs_ping = GNS3SimulationEngine._probe_command("10.0.1.2", "ping", base_type="host")
    cmd_vpcs_trace = GNS3SimulationEngine._probe_command("10.0.1.2", "traceroute", base_type="host")
    assert cmd_vpcs_ping == "ping 10.0.1.2 -c 3"
    assert cmd_vpcs_trace == "trace 10.0.1.2"

    # Linux (default)
    cmd_linux_ping = GNS3SimulationEngine._probe_command("10.0.1.2", "ping", base_type="router")
    cmd_linux_trace = GNS3SimulationEngine._probe_command("10.0.1.2", "traceroute", base_type="router")
    assert cmd_linux_ping == "ping -c 3 10.0.1.2"
    assert cmd_linux_trace == "traceroute -w 2 10.0.1.2"


async def test_parse_cisco_ping_output():
    raw_success = (
        "Sending 5, 100-byte ICMP Echos to 10.0.1.2, timeout is 2 seconds:\n"
        "!!!!!\n"
        "Success rate is 100 percent (5/5), round-trip min/avg/max = 1/3/8 ms\n"
    )
    result = GNS3SimulationEngine._parse_probe_output(raw_success, "ping", vendor="cisco")
    assert result.success is True
    assert result.rttMs == 3.0

    raw_fail = (
        "Sending 5, 100-byte ICMP Echos to 10.0.1.2, timeout is 2 seconds:\n"
        ".....\n"
        "Success rate is 0 percent (0/5)\n"
    )
    result_fail = GNS3SimulationEngine._parse_probe_output(raw_fail, "ping", vendor="cisco")
    assert result_fail.success is False
    assert result_fail.rttMs is None


async def test_parse_cisco_traceroute_output_with_msec():
    raw = (
        "Type escape sequence to abort.\n"
        "Tracing the route to 10.0.2.1\n"
        "  1 10.0.1.1 4 msec 3 msec 2 msec\n"
        "  2 10.0.2.1 8 msec 6 msec 5 msec\n"
    )
    result = GNS3SimulationEngine._parse_probe_output(raw, "traceroute", vendor="cisco")
    assert result.success is True
    assert len(result.hops) == 2
    assert result.hops[0]["ip"] == "10.0.1.1"
    assert result.hops[0]["rttMs"] == 4.0
    assert result.hops[1]["ip"] == "10.0.2.1"
    assert result.hops[1]["rttMs"] == 8.0


async def test_delete_topology_sends_delete_request():
    MockAsyncClient.response_queue = [response()]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )
    await engine.delete_topology("proj-123")
    assert MockAsyncClient.requests == [
        ("DELETE", "http://gns3.local/v2/projects/proj-123", {}),
    ]


async def test_link_payload_tracked_switch_and_router():
    from app.schemas.engine_plan import EngineLinkPlanSchema
    link = EngineLinkPlanSchema(
        id="link-1",
        sourceNodeId="sw1",
        sourcePort="eth0",
        targetNodeId="r1",
        targetPort="eth0",
        linkType="ethernet",
    )
    node_id_map = {"sw1": "gns3-sw1", "r1": "gns3-r1"}
    port_counters = {"sw1": 0, "r1": 0}
    node_types = {"sw1": "switch", "r1": "router"}

    payload = GNS3SimulationEngine._build_link_payload_tracked(
        link, node_id_map, port_counters, node_types
    )

    # sw1 is switch, so it increments port_number, keeping adapter_number=0
    assert payload["nodes"][0]["node_id"] == "gns3-sw1"
    assert payload["nodes"][0]["adapter_number"] == 0
    assert payload["nodes"][0]["port_number"] == 0

    # r1 is router, so it increments adapter_number, keeping port_number=0
    assert payload["nodes"][1]["node_id"] == "gns3-r1"
    assert payload["nodes"][1]["adapter_number"] == 0
    assert payload["nodes"][1]["port_number"] == 0

    # Let's add a second link to sw1 and r1
    link2 = EngineLinkPlanSchema(
        id="link-2",
        sourceNodeId="sw1",
        sourcePort="eth1",
        targetNodeId="r1",
        targetPort="eth1",
        linkType="ethernet",
    )
    payload2 = GNS3SimulationEngine._build_link_payload_tracked(
        link2, node_id_map, port_counters, node_types
    )

    # sw1 is switch, port_number should be 1
    assert payload2["nodes"][0]["node_id"] == "gns3-sw1"
    assert payload2["nodes"][0]["adapter_number"] == 0
    assert payload2["nodes"][0]["port_number"] == 1

    # r1 is router, adapter_number should be 1
    assert payload2["nodes"][1]["node_id"] == "gns3-r1"
    assert payload2["nodes"][1]["adapter_number"] == 1
    assert payload2["nodes"][1]["port_number"] == 0


async def test_telnet_command_success():
    received_command = None

    async def handle_telnet(reader, writer):
        nonlocal received_command
        writer.write(b"Welcome to console\r\n")
        await writer.drain()
        data = await reader.read(1024)
        received_command = data.decode().strip()
        writer.write(b"Output: ping success\r\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_telnet, "127.0.0.1", 0)
    async with server:
        host, port = server.sockets[0].getsockname()
        output = await GNS3SimulationEngine._telnet_command(host, port, "ping 10.0.1.2")
        assert received_command == "ping 10.0.1.2"
        assert "ping success" in output


async def test_telnet_command_connection_failure(monkeypatch):
    async def mock_open_connection(host, port):
        raise OSError("Connection refused")

    monkeypatch.setattr("asyncio.open_connection", mock_open_connection)

    with pytest.raises(GNS3AdapterError, match="Cannot connect to console"):
        await GNS3SimulationEngine._telnet_command("127.0.0.1", 9999, "ping")


async def test_telnet_command_reads_until_timeout(monkeypatch):
    async def handle_telnet(reader, writer):
        # Allow client to run its banner drain
        await asyncio.sleep(0.6)
        # Read the command sent by client
        await reader.read(1024)
        # Write response output
        writer.write(b"Initial output\r\n")
        await writer.drain()
        # Keep open but don't close, wait for timeout
        await asyncio.sleep(2.0)
        writer.close()
        await writer.wait_closed()

    # Speed up wait_for in test
    original_wait_for = asyncio.wait_for

    async def mock_wait_for(fut, timeout, **kwargs):
        if timeout == 3.0:
            timeout = 0.05
        return await original_wait_for(fut, timeout, **kwargs)

    monkeypatch.setattr("asyncio.wait_for", mock_wait_for)

    server = await asyncio.start_server(handle_telnet, "127.0.0.1", 0)
    async with server:
        host, port = server.sockets[0].getsockname()
        output = await GNS3SimulationEngine._telnet_command(host, port, "ping")
        assert "Initial output" in output



async def test_exec_console_command_fast_path_success():
    MockAsyncClient.response_queue = [
        response(payload={"output": "HTTP console output"})
    ]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    output = await engine._exec_console_command("proj-1", "gns3-node-1", "show ip route")

    assert output == "HTTP console output"
    assert MockAsyncClient.requests == [
        ("POST", "http://gns3.local/v2/projects/proj-1/nodes/gns3-node-1/console", {"json": {"command": "show ip route"}})
    ]


async def test_exec_console_command_fallback_to_telnet(monkeypatch):
    MockAsyncClient.response_queue = [
        response(status_code=404),  # HTTP console endpoint not found
        response(payload={"console": 5001, "console_host": "127.0.0.2"})  # node info
    ]

    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    called_telnet = []

    async def mock_telnet_command(host, port, command):
        called_telnet.append((host, port, command))
        return "Telnet response"

    monkeypatch.setattr(engine, "_telnet_command", mock_telnet_command)

    output = await engine._exec_console_command("proj-1", "gns3-node-1", "show version")

    assert output == "Telnet response"
    assert len(called_telnet) == 1
    assert called_telnet[0] == ("127.0.0.2", 5001, "show version")
    assert len(MockAsyncClient.requests) == 2
    assert MockAsyncClient.requests[0][1] == "http://gns3.local/v2/projects/proj-1/nodes/gns3-node-1/console"
    assert MockAsyncClient.requests[1][1] == "http://gns3.local/v2/projects/proj-1/nodes/gns3-node-1"


async def test_exec_console_command_missing_console_port_raises():
    MockAsyncClient.response_queue = [
        response(status_code=404),
        response(payload={"console": None, "console_host": "127.0.0.1"})
    ]
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    with pytest.raises(GNS3AdapterError, match="has no console port; cannot execute probe"):
        await engine._exec_console_command("proj-1", "gns3-node-1", "ping")


async def test_run_probe_success(monkeypatch):
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )
    from app.engines.gns3 import _NodeEntry
    engine._node_registry["r1"] = _NodeEntry(
        project_id="proj-1",
        gns3_node_id="gns3-r1",
        base_type="router",
        vendor="cisco"
    )

    async def mock_exec(project_id, node_id, command):
        assert project_id == "proj-1"
        assert node_id == "gns3-r1"
        assert command == "ping 10.0.1.2 repeat 3"
        return (
            "Sending 5, 100-byte ICMP Echos to 10.0.1.2, timeout is 2 seconds:\n"
            "!!!!!\n"
            "Success rate is 100 percent (5/5), round-trip min/avg/max = 1/3/8 ms\n"
        )

    monkeypatch.setattr(engine, "_exec_console_command", mock_exec)

    result = await engine.run_probe("r1", "10.0.1.2", "ping")
    assert result.success is True
    assert result.rttMs == 3.0


async def test_clear_fault_unregistered_link_raises():
    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )
    with pytest.raises(GNS3AdapterError, match="not found in GNS3 registry"):
        await engine.clear_fault("unknown-link")


async def test_http_invalid_json_raises_adapter_error():
    resp = httpx.Response(200, content=b"Not JSON at all", request=httpx.Request("POST", "http://gns3.local"))
    MockAsyncClient.response_queue = [resp]

    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    with pytest.raises(GNS3AdapterError, match="GNS3 returned invalid JSON"):
        await engine.start_topology("project-1")


async def test_http_status_error_raises_adapter_error():
    resp = httpx.Response(500, content=b"Internal Server Error", request=httpx.Request("POST", "http://gns3.local"))
    MockAsyncClient.response_queue = [resp]

    engine = GNS3SimulationEngine(
        base_url="http://gns3.local",
        user="admin",
        password="secret",
    )

    with pytest.raises(GNS3AdapterError, match="GNS3 request failed"):
        await engine.start_topology("project-1")

