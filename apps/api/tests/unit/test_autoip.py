from app.schemas.topology import NetworkNodeSchema, NetworkLinkSchema
from app.services.autoip import assign_topology_ips

def test_assign_loopbacks_to_l3():
    nodes = [
        NetworkNodeSchema(id="router1", label="R1", position={"x": 0, "y": 0}, baseType="router", tags=[]),
        NetworkNodeSchema(id="switch1", label="SW1", position={"x": 0, "y": 0}, baseType="switch", tags=[]),
        NetworkNodeSchema(id="host1", label="H1", position={"x": 0, "y": 0}, baseType="host", tags=[])
    ]
    edges = []
    
    nodes, edges = assign_topology_ips(nodes, edges)
    
    # router1 e switch1 non dovrebbero avere loopback auto-assegnati per nuova policy
    assert nodes[0].id == "router1"
    assert not nodes[0].logicalConfig.get("loopback")
    
    assert nodes[1].id == "switch1"
    assert not nodes[1].logicalConfig.get("loopback")
    
    # host1 non è L3, non dovrebbe avere loopback
    assert nodes[2].id == "host1"
    assert not nodes[2].logicalConfig

def test_assign_p2p_subnets():
    nodes = []
    edges = [
        NetworkLinkSchema(id="link2", sourceNodeId="r2", targetNodeId="r3", sourcePort="g1", targetPort="g1", linkType="ethernet"),
        NetworkLinkSchema(id="link1", sourceNodeId="r1", targetNodeId="r2", sourcePort="g1", targetPort="g0", linkType="ethernet"),
    ]
    
    nodes, edges = assign_topology_ips(nodes, edges)
    
    # I link dovrebbero essere processati per ID: link1 poi link2
    sorted_edges = sorted(edges, key=lambda x: x.id)
    
    # P2P pool starts at 10.0.1.0/30 per ARCHITECTURE.md §5
    assert sorted_edges[0].id == "link1"
    assert sorted_edges[0].ipConfig["subnet"] == "10.0.1.0/30"
    assert sorted_edges[0].ipConfig["sourceIp"] == "10.0.1.1"
    assert sorted_edges[0].ipConfig["targetIp"] == "10.0.1.2"
    
    assert sorted_edges[1].id == "link2"
    assert sorted_edges[1].ipConfig["subnet"] == "10.0.1.4/30"
    assert sorted_edges[1].ipConfig["sourceIp"] == "10.0.1.5"
    assert sorted_edges[1].ipConfig["targetIp"] == "10.0.1.6"

def test_idempotence():
    nodes = [
        NetworkNodeSchema(id="router1", label="R1", position={"x": 0, "y": 0}, baseType="router", logicalConfig={"loopback": "10.255.0.100"}, tags=[]),
    ]
    edges = [
        NetworkLinkSchema(id="link1", sourceNodeId="r1", targetNodeId="r2", sourcePort="g1", targetPort="g0", linkType="ethernet", ipConfig={"subnet": "10.0.0.8/30"}),
    ]
    
    nodes, edges = assign_topology_ips(nodes, edges)
    
    assert nodes[0].logicalConfig["loopback"] == "10.255.0.100"
    assert edges[0].ipConfig["subnet"] == "10.0.0.8/30"

def test_conflict_avoidance():
    nodes = [
        NetworkNodeSchema(id="router1", label="R1", position={"x": 0, "y": 0}, baseType="router", logicalConfig={"loopback": "10.255.0.1"}, tags=[]),
        NetworkNodeSchema(id="router2", label="R2", position={"x": 0, "y": 0}, baseType="router", tags=[]),
    ]
    edges = [
        NetworkLinkSchema(id="link1", sourceNodeId="r1", targetNodeId="r2", sourcePort="g1", targetPort="g0", linkType="ethernet", ipConfig={"subnet": "10.0.1.0/30"}),
        NetworkLinkSchema(id="link2", sourceNodeId="r2", targetNodeId="r3", sourcePort="g1", targetPort="g1", linkType="ethernet"),
    ]

    nodes, edges = assign_topology_ips(nodes, edges)

    # router2 non riceve un loopback auto-assegnato
    assert not nodes[1].logicalConfig.get("loopback")

    # link2 skip 10.0.1.0/30 (already used) and gets 10.0.1.4/30
    sorted_edges = sorted(edges, key=lambda x: x.id)
    assert sorted_edges[1].ipConfig["subnet"] == "10.0.1.4/30"


def test_logical_links_are_skipped():
    """Link di tipo 'logical' non devono ricevere IP — sono overlay/virtuali."""
    nodes = []
    edges = [
        NetworkLinkSchema(id="link1", sourceNodeId="r1", targetNodeId="r2", sourcePort="g0", targetPort="g0", linkType="logical"),
        NetworkLinkSchema(id="link2", sourceNodeId="r1", targetNodeId="r2", sourcePort="g1", targetPort="g1", linkType="ethernet"),
    ]

    nodes, edges = assign_topology_ips(nodes, edges)

    sorted_edges = sorted(edges, key=lambda x: x.id)
    # link1 (logical) → nessun IP
    assert sorted_edges[0].ipConfig is None or not sorted_edges[0].ipConfig.get("subnet")
    # link2 (ethernet) → IP assegnato normalmente
    assert sorted_edges[1].ipConfig is not None
    assert sorted_edges[1].ipConfig.get("subnet") is not None


def test_empty_topology():
    """Topologia vuota non deve sollevare eccezioni e restituisce liste vuote."""
    nodes, edges = assign_topology_ips([], [])
    assert nodes == []
    assert edges == []


def test_host_nodes_do_not_get_loopback():
    """Solo nodi L3 (router, switch, firewall) ricevono loopback — host e cloud no."""
    nodes = [
        NetworkNodeSchema(id="host1", label="H1", position={"x": 0, "y": 0}, baseType="host", tags=[]),
        NetworkNodeSchema(id="cloud1", label="C1", position={"x": 0, "y": 0}, baseType="cloud", tags=[]),
        NetworkNodeSchema(id="fw1", label="FW1", position={"x": 0, "y": 0}, baseType="firewall", tags=[]),
    ]

    nodes, edges = assign_topology_ips(nodes, [])

    node_map = {n.id: n for n in nodes}
    assert not node_map["host1"].logicalConfig
    assert not node_map["cloud1"].logicalConfig
    assert node_map["fw1"].logicalConfig is not None
    assert not node_map["fw1"].logicalConfig.get("loopback")


def test_determinism_multiple_runs():
    """Passando lo stesso input due volte si ottiene sempre lo stesso output."""
    nodes = [
        NetworkNodeSchema(id="r1", label="R1", position={"x": 0, "y": 0}, baseType="router", tags=[]),
        NetworkNodeSchema(id="r2", label="R2", position={"x": 0, "y": 0}, baseType="router", tags=[]),
    ]
    edges = [
        NetworkLinkSchema(id="link-ab", sourceNodeId="r1", targetNodeId="r2", sourcePort="g0", targetPort="g0", linkType="ethernet"),
    ]

    # Prima esecuzione
    import copy
    nodes_run1, edges_run1 = assign_topology_ips(copy.deepcopy(nodes), copy.deepcopy(edges))
    # Seconda esecuzione — stesso input, stesse istanze fresche
    nodes_run2, edges_run2 = assign_topology_ips(copy.deepcopy(nodes), copy.deepcopy(edges))

    assert nodes_run1[0].logicalConfig == nodes_run2[0].logicalConfig
    assert nodes_run1[1].logicalConfig == nodes_run2[1].logicalConfig
    assert edges_run1[0].ipConfig == edges_run2[0].ipConfig
