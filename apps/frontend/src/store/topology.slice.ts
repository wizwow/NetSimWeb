import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { NetworkNode, NetworkLink } from '@octet/shared-types';
import type { Connection, EdgeChange, NodeChange } from '@xyflow/react';
import { v4 as uuidv4 } from 'uuid';

// Re-export from canvas helpers so the rest of the app
// never needs to import @xyflow/react directly.
import type { ReactFlowNode, ReactFlowEdge } from '../canvas/graphHelpers';
import {
  applyNodeChangesTyped,
  applyEdgeChangesTyped,
  addEdgeTyped,
  toReactFlowNode,
  toReactFlowEdge,
  getNextFreePort,
} from '../canvas/graphHelpers';

export type { ReactFlowNode, ReactFlowEdge };

interface TopologyState {
  currentTopologyId: string | null;
  currentTopologyName: string;
  nodes: ReactFlowNode[];
  edges: ReactFlowEdge[];
  selectedNodeIds: string[];
  selectedEdgeIds: string[];

  // Pure state mutations (no I/O)
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  addNode: (node: NetworkNode) => void;
  removeNodes: (nodeIds: string[]) => void;
  updateNodeStatus: (nodeId: string, status: NonNullable<NetworkNode['runtimeState']>['status']) => void;
  updateNode: (nodeId: string, updates: Partial<NetworkNode>) => void;
  updateNodeInterface: (nodeId: string, ifaceName: string, updates: { ip?: string; subnet?: string }) => void;
  updateEdge: (edgeId: string, updates: Partial<NetworkLink>) => void;
  updateEdgeFault: (edgeId: string, faultState: NetworkLink['faultState']) => void;

  // Bulk setters used by hooks that perform I/O
  setCurrentTopologyId: (id: string | null) => void;
  setCurrentTopologyName: (name: string) => void;
  replaceGraph: (nodes: NetworkNode[], edges: NetworkLink[]) => void;
  setAllNodesStatus: (status: NonNullable<NetworkNode['runtimeState']>['status']) => void;
}

export const useTopologyStore = create<TopologyState>()(
  immer((set) => ({
    currentTopologyId: null,
    currentTopologyName: 'New Topology',
    nodes: [],
    edges: [],
    selectedNodeIds: [],
    selectedEdgeIds: [],

    onNodesChange: (changes) => set((state) => {
      state.nodes = applyNodeChangesTyped(changes, state.nodes);
    }),

    onEdgesChange: (changes) => set((state) => {
      // Free interface slots before the edge is removed from the array
      for (const change of changes) {
        if (change.type === 'remove') {
          const edge = state.edges.find(e => e.id === change.id);
          if (edge?.data) {
            const srcNode = state.nodes.find(n => n.id === edge.source);
            const srcIface = srcNode?.data.logicalConfig?.interfaces.find(
              i => i.name === edge.data!.sourcePort,
            );
            if (srcIface) srcIface.status = 'down';

            const tgtNode = state.nodes.find(n => n.id === edge.target);
            const tgtIface = tgtNode?.data.logicalConfig?.interfaces.find(
              i => i.name === edge.data!.targetPort,
            );
            if (tgtIface) tgtIface.status = 'down';
          }
        }
      }
      state.edges = applyEdgeChangesTyped(changes, state.edges);
    }),

    onConnect: (connection) => set((state) => {
      const sourceNode = state.nodes.find(n => n.id === connection.source);
      const targetNode = state.nodes.find(n => n.id === connection.target);
      if (!sourceNode || !targetNode) return;

      const sourcePort = getNextFreePort(
        connection.source!,
        sourceNode.data.logicalConfig?.interfaces ?? [],
        state.edges,
        connection.sourceHandle ?? undefined,
      );
      const targetPort = getNextFreePort(
        connection.target!,
        targetNode.data.logicalConfig?.interfaces ?? [],
        state.edges,
        connection.targetHandle ?? undefined,
      );

      // Silently refuse if either node has no free interfaces left
      if (!sourcePort || !targetPort) return;

      // Mark those interfaces as in-use
      const srcIface = sourceNode.data.logicalConfig?.interfaces.find(i => i.name === sourcePort);
      const tgtIface = targetNode.data.logicalConfig?.interfaces.find(i => i.name === targetPort);
      if (srcIface) srcIface.status = 'up';
      if (tgtIface) tgtIface.status = 'up';

      const newEdge: ReactFlowEdge = {
        id: `edge-${uuidv4()}`,
        source: connection.source!,
        target: connection.target!,
        sourceHandle: connection.sourceHandle,
        targetHandle: connection.targetHandle,
        type: 'simulatedEdge',
        data: {
          id: `lnk-${uuidv4()}`,
          sourceNodeId: connection.source!,
          targetNodeId: connection.target!,
          sourcePort,
          targetPort,
          linkType: 'ethernet',
        },
      };
      state.edges = addEdgeTyped(newEdge, state.edges);
    }),

    addNode: (networkNode) => set((state) => {
      state.nodes.push(toReactFlowNode(networkNode));
    }),

    removeNodes: (nodeIds) => set((state) => {
      state.nodes = state.nodes.filter(n => !nodeIds.includes(n.id));
      state.edges = state.edges.filter(e => !nodeIds.includes(e.source) && !nodeIds.includes(e.target));
    }),

    updateNodeStatus: (nodeId, status) => set((state) => {
      const node = state.nodes.find(n => n.id === nodeId);
      if (node) {
        if (!node.data.runtimeState) node.data.runtimeState = { status: 'stopped' };
        node.data.runtimeState.status = status;
      }
    }),

    updateNode: (nodeId, updates) => set((state) => {
      const node = state.nodes.find(n => n.id === nodeId);
      if (node) {
        node.data = { ...node.data, ...updates };
        if (updates.label) node.data.label = updates.label;
      }
    }),

    updateNodeInterface: (nodeId, ifaceName, updates) => set((state) => {
      const node = state.nodes.find(n => n.id === nodeId);
      if (!node?.data.logicalConfig) return;
      const iface = node.data.logicalConfig.interfaces.find(i => i.name === ifaceName);
      if (!iface) return;
      if (updates.ip !== undefined) iface.ip = updates.ip || undefined;
      if (updates.subnet !== undefined) iface.subnet = updates.subnet || undefined;
    }),

    updateEdge: (edgeId, updates) => set((state) => {
      const edge = state.edges.find(e => e.id === edgeId);
      if (edge && edge.data) {
        Object.assign(edge.data, updates);
        if (updates.ipConfig?.subnet) {
          edge.label = updates.ipConfig.subnet;
        }
      }
    }),

    updateEdgeFault: (edgeId, faultState) => set((state) => {
      const edge = state.edges.find(e => e.id === edgeId || e.data?.id === edgeId);
      if (edge && edge.data) {
        edge.data.faultState = faultState;
      }
    }),

    setCurrentTopologyId: (id) => set((state) => {
      state.currentTopologyId = id;
    }),

    setCurrentTopologyName: (name) => set((state) => {
      state.currentTopologyName = name;
    }),

    replaceGraph: (nodes, edges) => set((state) => {
      state.nodes = nodes.map(toReactFlowNode);
      state.edges = edges.map(toReactFlowEdge);
    }),

    setAllNodesStatus: (status) => set((state) => {
      state.nodes.forEach(n => {
        if (!n.data.runtimeState) n.data.runtimeState = { status: 'stopped' };
        n.data.runtimeState.status = status;
      });
    }),
  })),
);
