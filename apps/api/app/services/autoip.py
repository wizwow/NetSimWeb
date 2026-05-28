import ipaddress
from typing import List, Tuple
from app.schemas.topology import NetworkNodeSchema, NetworkLinkSchema

# Pool defaults — documentati in ARCHITECTURE.md §5
_P2P_POOL = "10.0.0.0/8"        # P2P base pool; first /30 allocated is 10.0.1.0/30
_P2P_SKIP_PREFIX = 64            # Skip 64 /30 subnets (10.0.0.0–10.0.0.252) = start at 10.0.1.0
_LOOPBACK_POOL = "10.255.0.0/16"  # Loopback /32: 10.255.0.1, …
_L3_TYPES = frozenset({"router", "switch", "firewall"})


class IPConflictError(Exception):
    """Raised when an IP assignment would overlap an existing allocation."""


def _collect_used_networks(
    nodes: List[NetworkNodeSchema],
    edges: List[NetworkLinkSchema],
) -> List[ipaddress.IPv4Network]:
    """Gather all subnets/loopbacks already claimed by the topology."""
    used: List[ipaddress.IPv4Network] = []
    for edge in edges:
        if edge.ipConfig and edge.ipConfig.get("subnet"):
            try:
                used.append(ipaddress.IPv4Network(edge.ipConfig["subnet"]))
            except ValueError:
                pass
    for node in nodes:
        if node.logicalConfig and node.logicalConfig.get("loopback"):
            try:
                used.append(ipaddress.IPv4Network(f"{node.logicalConfig['loopback']}/32"))
            except ValueError:
                pass
    return used


def _is_conflict(candidate: ipaddress.IPv4Network, used: List[ipaddress.IPv4Network]) -> bool:
    return any(candidate.overlaps(u) for u in used)


def assign_topology_ips(
    nodes: List[NetworkNodeSchema],
    edges: List[NetworkLinkSchema],
    p2p_pool: str = _P2P_POOL,
    loopback_pool: str = _LOOPBACK_POOL,
) -> Tuple[List[NetworkNodeSchema], List[NetworkLinkSchema]]:
    """
    Return the topology with all missing IPs filled in.
    Does not modify IPs already present.  Idempotent.
    """
    used_networks = _collect_used_networks(nodes, edges)

    # --- Loopback assignment (L3 nodes only) ---
    # Per user request, Loopbacks are no longer automatically assigned.
    # They can still be manually configured in the UI.
    sorted_nodes = sorted(nodes, key=lambda x: x.id)
    for node in sorted_nodes:
        if node.baseType in _L3_TYPES:
            logical = node.logicalConfig or {}
            # We explicitly do NOT auto-generate loopbacks anymore
            node.logicalConfig = logical

    # --- P2P /30 assignment ---
    sorted_edges = sorted(edges, key=lambda x: x.id)
    _p2p_all = ipaddress.IPv4Network(p2p_pool).subnets(new_prefix=30)
    # Skip the first 64 /30 subnets (10.0.0.0 – 10.0.0.252)
    # so allocation starts at 10.0.1.0/30 per ARCHITECTURE.md
    for _ in range(_P2P_SKIP_PREFIX):
        next(_p2p_all, None)
    p2p_gen = _p2p_all

    for edge in sorted_edges:
        if edge.linkType != "logical":
            ip_cfg = edge.ipConfig or {}
            if not ip_cfg.get("subnet"):
                while True:
                    try:
                        candidate_net = next(p2p_gen)
                        if not _is_conflict(candidate_net, used_networks):
                            hosts = list(candidate_net.hosts())
                            ip_cfg["subnet"] = str(candidate_net)
                            ip_cfg["sourceIp"] = str(hosts[0])
                            ip_cfg["targetIp"] = str(hosts[1])
                            used_networks.append(candidate_net)
                            break
                    except StopIteration:
                        break
            edge.ipConfig = ip_cfg

    return nodes, edges
