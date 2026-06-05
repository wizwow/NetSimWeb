/**
 * React Flow graph helpers.
 *
 * These utilities depend on @xyflow/react and MUST stay inside `canvas/`
 * so the store layer never imports React Flow directly (ARCHITECTURE.md §2.2).
 */
import { applyNodeChanges, applyEdgeChanges, addEdge } from '@xyflow/react';
import type { Node, Edge, NodeChange, EdgeChange } from '@xyflow/react';
import type { NetworkNode, NetworkLink } from '@netsimflow/shared-types';

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
