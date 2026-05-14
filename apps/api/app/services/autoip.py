import ipaddress
from typing import List, Tuple
from app.schemas.topology import NetworkNodeSchema, NetworkLinkSchema

def assign_topology_ips(
    nodes: List[NetworkNodeSchema], 
    edges: List[NetworkLinkSchema], 
    base_pool: str = "10.0.0.0/8",
    loopback_pool: str = "10.255.0.0/16"
) -> Tuple[List[NetworkNodeSchema], List[NetworkLinkSchema]]:
    
    # 1. Trova tutte le subnet già utilizzate (per non sovrascrivere o creare conflitti)
    used_networks = []
    
    for edge in edges:
        if edge.ipConfig and edge.ipConfig.get("subnet"):
            try:
                used_networks.append(ipaddress.IPv4Network(edge.ipConfig["subnet"]))
            except ValueError:
                pass
                
    for node in nodes:
        if node.logicalConfig and node.logicalConfig.get("loopback"):
            try:
                used_networks.append(ipaddress.IPv4Network(f"{node.logicalConfig['loopback']}/32"))
            except ValueError:
                pass

    # Funzione helper per verificare i conflitti
    def is_conflict(net: ipaddress.IPv4Network) -> bool:
        for used in used_networks:
            if net.overlaps(used):
                return True
        return False

    # 2. Assegna Loopback ai nodi L3 (router, switch)
    # Ordiniamo i nodi per ID in modo alfabetico per garantire il determinismo
    sorted_nodes = sorted(nodes, key=lambda x: x.id)
    l3_types = ["router", "switch", "firewall"]
    
    loopback_gen = ipaddress.IPv4Network(loopback_pool).hosts()
    
    for node in sorted_nodes:
        if node.baseType in l3_types:
            logical = node.logicalConfig or {}

            if not logical.get("loopback"):
                # Cerca il prossimo loopback disponibile
                while True:
                    try:
                        candidate_ip = next(loopback_gen)
                        candidate_net = ipaddress.IPv4Network(f"{candidate_ip}/32")
                        if not is_conflict(candidate_net):
                            logical["loopback"] = str(candidate_ip)
                            used_networks.append(candidate_net)
                            break
                    except StopIteration:
                        break # Pool esaurito
            node.logicalConfig = logical

    # 3. Assegna IP ai link Point-to-Point (/30)
    # Ordiniamo i link per ID
    sorted_edges = sorted(edges, key=lambda x: x.id)
    
    p2p_pool = ipaddress.IPv4Network(base_pool)
    p2p_gen = p2p_pool.subnets(new_prefix=30)
    
    for edge in sorted_edges:
        if edge.linkType != "logical": # Assegniamo IP ai link fisici/tunnel
            ip_cfg = edge.ipConfig or {}

            if not ip_cfg.get("subnet"):
                while True:
                    try:
                        candidate_net = next(p2p_gen)
                        if not is_conflict(candidate_net):
                            # /30 has 4 IPs: network, host1, host2, broadcast
                            hosts = list(candidate_net.hosts())
                            ip_cfg["subnet"] = str(candidate_net)
                            ip_cfg["sourceIp"] = str(hosts[0])
                            ip_cfg["targetIp"] = str(hosts[1])
                            used_networks.append(candidate_net)
                            break
                    except StopIteration:
                        break # Pool esaurito
            edge.ipConfig = ip_cfg

    return nodes, edges
