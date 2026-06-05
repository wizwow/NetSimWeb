from collections import defaultdict
from typing import Dict, List

from app.schemas.engine_plan import (
    EngineDeploymentPlanSchema,
    EngineInterfacePlanSchema,
    EngineLinkPlanSchema,
    EngineNodePlanSchema,
)
from app.schemas.topology import NetworkLinkSchema, NetworkNodeSchema, TopologyBase


class TopologyTranslationError(ValueError):
    """Raised when a logical topology cannot be translated for an engine."""


ENGINE_KIND_BY_BASE_TYPE = {
    "router": "network-device",
    "switch": "network-device",
    "firewall": "network-device",
    "host": "host",
    "cloud": "cloud",
    "site": "site",
}

SUPPORTED_LINK_TYPES = {"ethernet"}


def translate_topology_to_engine_plan(topology: TopologyBase) -> EngineDeploymentPlanSchema:
    """Convert a logical Octet topology into an engine-neutral plan."""

    node_by_id = _index_nodes(topology.nodes)
    _validate_links(topology.edges, node_by_id)

    interfaces_by_node = _derive_interfaces(topology.edges)

    nodes = [
        _translate_node(node, interfaces_by_node.get(node.id, []))
        for node in topology.nodes
    ]
    links = [_translate_link(link) for link in topology.edges]

    return EngineDeploymentPlanSchema(
        name=topology.name,
        abstractionLevel=topology.abstraction_level,
        nodeCount=len(nodes),
        linkCount=len(links),
        nodes=nodes,
        links=links,
    )


def _index_nodes(nodes: List[NetworkNodeSchema]) -> Dict[str, NetworkNodeSchema]:
    node_by_id: Dict[str, NetworkNodeSchema] = {}
    for node in nodes:
        if node.id in node_by_id:
            raise TopologyTranslationError(f"Duplicate node id '{node.id}'")
        node_by_id[node.id] = node
    return node_by_id


def _validate_links(
    links: List[NetworkLinkSchema],
    node_by_id: Dict[str, NetworkNodeSchema],
) -> None:
    seen_link_ids: set[str] = set()
    for link in links:
        if link.id in seen_link_ids:
            raise TopologyTranslationError(f"Duplicate link id '{link.id}'")
        seen_link_ids.add(link.id)

        if link.linkType not in SUPPORTED_LINK_TYPES:
            raise TopologyTranslationError(
                f"Unsupported link type '{link.linkType}' for link '{link.id}'"
            )
        if link.sourceNodeId not in node_by_id:
            raise TopologyTranslationError(
                f"Link '{link.id}' references missing source node '{link.sourceNodeId}'"
            )
        if link.targetNodeId not in node_by_id:
            raise TopologyTranslationError(
                f"Link '{link.id}' references missing target node '{link.targetNodeId}'"
            )


def _derive_interfaces(
    links: List[NetworkLinkSchema],
) -> Dict[str, List[EngineInterfacePlanSchema]]:
    interfaces: Dict[str, List[EngineInterfacePlanSchema]] = defaultdict(list)
    for link in links:
        ip_config = link.ipConfig or {}
        subnet = ip_config.get("subnet")
        interfaces[link.sourceNodeId].append(
            EngineInterfacePlanSchema(
                nodeId=link.sourceNodeId,
                port=link.sourcePort,
                peerNodeId=link.targetNodeId,
                peerPort=link.targetPort,
                linkId=link.id,
                ip=ip_config.get("sourceIp"),
                subnet=subnet,
            )
        )
        interfaces[link.targetNodeId].append(
            EngineInterfacePlanSchema(
                nodeId=link.targetNodeId,
                port=link.targetPort,
                peerNodeId=link.sourceNodeId,
                peerPort=link.sourcePort,
                linkId=link.id,
                ip=ip_config.get("targetIp"),
                subnet=subnet,
            )
        )
    return dict(interfaces)


def _translate_node(
    node: NetworkNodeSchema,
    interfaces: List[EngineInterfacePlanSchema],
) -> EngineNodePlanSchema:
    logical_config = node.logicalConfig or {}
    vendor_spec = node.vendorSpec

    return EngineNodePlanSchema(
        id=node.id,
        label=node.label,
        baseType=node.baseType,
        engineKind=ENGINE_KIND_BY_BASE_TYPE[node.baseType],
        role=node.role,
        protocols=node.protocols or [],
        loopback=logical_config.get("loopback"),
        vendor=vendor_spec.vendor if vendor_spec else None,
        platform=vendor_spec.platform if vendor_spec else None,
        imageRef=vendor_spec.imageRef if vendor_spec else None,
        interfaces=interfaces,
    )


def _translate_link(link: NetworkLinkSchema) -> EngineLinkPlanSchema:
    ip_config = link.ipConfig or {}

    return EngineLinkPlanSchema(
        id=link.id,
        sourceNodeId=link.sourceNodeId,
        sourcePort=link.sourcePort,
        targetNodeId=link.targetNodeId,
        targetPort=link.targetPort,
        linkType=link.linkType,
        subnet=ip_config.get("subnet"),
        sourceIp=ip_config.get("sourceIp"),
        targetIp=ip_config.get("targetIp"),
        qos=link.qos.model_dump() if link.qos else None,
        faultState=link.faultState.model_dump() if link.faultState else None,
    )
