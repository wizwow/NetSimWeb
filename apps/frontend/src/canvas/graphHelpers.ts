/**
 * React Flow graph helpers.
 *
 * These utilities depend on @xyflow/react and MUST stay inside `canvas/`
 * so the store layer never imports React Flow directly (ARCHITECTURE.md §2.2).
 */
import { applyNodeChanges, applyEdgeChanges, addEdge } from '@xyflow/react';
import type { Node, Edge, NodeChange, EdgeChange } from '@xyflow/react';
import type { NetworkNode, NetworkLink, LogicalInterface } from '@netsimflow/shared-types';

export type ReactFlowNode = Node<NetworkNode>;
export type ReactFlowEdge = Edge<NetworkLink>;

export function applyNodeChangesTyped(
  changes: NodeChange[],
  nodes: ReactFlowNode[],
): ReactFlowNode[] {
  return applyNodeChanges<ReactFlowNode>(
    changes as NodeChange<ReactFlowNode>[],
    nodes,
  );
}

export function applyEdgeChangesTyped(
  changes: EdgeChange[],
  edges: ReactFlowEdge[],
): ReactFlowEdge[] {
  return applyEdgeChanges<ReactFlowEdge>(
    changes as EdgeChange<ReactFlowEdge>[],
    edges,
  );
}

export function addEdgeTyped(
  edge: ReactFlowEdge,
  edges: ReactFlowEdge[],
): ReactFlowEdge[] {
  return addEdge<ReactFlowEdge>(edge, edges);
}

/** Convert a NetworkNode to a ReactFlow Node. */
export function toReactFlowNode(n: NetworkNode): ReactFlowNode {
  return {
    id: n.id,
    type: n.baseType,
    position: n.position,
    data: n,
  };
}

/**
 * Find the first interface on `nodeId` not already bound to an existing edge.
 * Checks both source-side and target-side usage so the result is always
 * the truly next free port regardless of which end of a link the node is on.
 * Returns the interface name (e.g. 'eth1') or null when all ports are occupied.
 */
export function getNextFreePort(
  nodeId: string,
  interfaces: LogicalInterface[],
  edges: ReactFlowEdge[],
): string | null {
  const usedPorts = new Set<string>([
    ...edges.filter(e => e.source === nodeId).map(e => e.data?.sourcePort ?? ''),
    ...edges.filter(e => e.target === nodeId).map(e => e.data?.targetPort ?? ''),
  ].filter(p => p !== ''));

  return interfaces.find(i => !usedPorts.has(i.name))?.name ?? null;
}

/** Convert a NetworkLink to a ReactFlow Edge. */
export function toReactFlowEdge(e: NetworkLink): ReactFlowEdge {
  return {
    id: e.id,
    type: 'simulatedEdge',
    source: e.sourceNodeId,
    target: e.targetNodeId,
    sourceHandle: e.sourcePort,
    targetHandle: e.targetPort,
    label: e.ipConfig?.subnet || '',
    data: e,
  };
}
