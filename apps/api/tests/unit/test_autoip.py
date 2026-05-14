import pytest
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
    
    # router1 e switch1 dovrebbero avere loopback
    # L'ordinamento alfabetico per id darà prima router1 poi switch1
    assert nodes[0].id == "router1"
    assert nodes[0].logicalConfig["loopback"] == "10.255.0.1"
    
    assert nodes[1].id == "switch1"
    assert nodes[1].logicalConfig["loopback"] == "10.255.0.2"
    
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
    
    assert sorted_edges[0].id == "link1"
    assert sorted_edges[0].ipConfig["subnet"] == "10.0.0.0/30"
    assert sorted_edges[0].ipConfig["sourceIp"] == "10.0.0.1"
    assert sorted_edges[0].ipConfig["targetIp"] == "10.0.0.2"
    
    assert sorted_edges[1].id == "link2"
    assert sorted_edges[1].ipConfig["subnet"] == "10.0.0.4/30"
    assert sorted_edges[1].ipConfig["sourceIp"] == "10.0.0.5"
    assert sorted_edges[1].ipConfig["targetIp"] == "10.0.0.6"

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
        NetworkLinkSchema(id="link1", sourceNodeId="r1", targetNodeId="r2", sourcePort="g1", targetPort="g0", linkType="ethernet", ipConfig={"subnet": "10.0.0.0/30"}),
        NetworkLinkSchema(id="link2", sourceNodeId="r2", targetNodeId="r3", sourcePort="g1", targetPort="g1", linkType="ethernet"),
    ]
    
    nodes, edges = assign_topology_ips(nodes, edges)
    
    # router2 skip 10.255.0.1 and gets 10.255.0.2
    assert nodes[1].logicalConfig["loopback"] == "10.255.0.2"
    
    # link2 skip 10.0.0.0/30 and gets 10.0.0.4/30
    sorted_edges = sorted(edges, key=lambda x: x.id)
    assert sorted_edges[1].ipConfig["subnet"] == "10.0.0.4/30"
