import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { NetworkNode, NetworkLink } from '@netsimflow/shared-types';
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
} from '../canvas/graphHelpers';

export type { ReactFlowNode, ReactFlowEdge };

interface TopologyState {
  currentTopologyId: string | null;
  nodes: ReactFlowNode[];
  edges: ReactFlowEdge[];
  selectedNodeIds: string[];
  selectedEdgeIds: string[];

  // Pure state mutations (no I/O)
  onNodesChange: (changes: any[]) => void;
  onEdgesChange: (changes: any[]) => void;
  onConnect: (connection: any) => void;
  addNode: (node: NetworkNode) => void;
  removeNodes: (nodeIds: string[]) => void;
  updateNodeStatus: (nodeId: string, status: NonNullable<NetworkNode['runtimeState']>['status']) => void;
  updateNode: (nodeId: string, updates: Partial<NetworkNode>) => void;
  updateEdge: (edgeId: string, updates: Partial<NetworkLink>) => void;

  // Bulk setters used by hooks that perform I/O
  setCurrentTopologyId: (id: string | null) => void;
  replaceGraph: (nodes: NetworkNode[], edges: NetworkLink[]) => void;
  setAllNodesStatus: (status: NonNullable<NetworkNode['runtimeState']>['status']) => void;
}

export const useTopologyStore = create<TopologyState>()(
  immer((set) => ({
    currentTopologyId: null,
    nodes: [],
    edges: [],
    selectedNodeIds: [],
    selectedEdgeIds: [],

    onNodesChange: (changes) => set((state) => {
      state.nodes = applyNodeChangesTyped(changes, state.nodes);
    }),

    onEdgesChange: (changes) => set((state) => {
      state.edges = applyEdgeChangesTyped(changes, state.edges);
    }),

    onConnect: (connection) => set((state) => {
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
          sourcePort: connection.sourceHandle || 'default',
          targetPort: connection.targetHandle || 'default',
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

    updateEdge: (edgeId, updates) => set((state) => {
      const edge = state.edges.find(e => e.id === edgeId);
      if (edge && edge.data) {
        Object.assign(edge.data, updates);
        if (updates.ipConfig?.subnet) {
          edge.label = updates.ipConfig.subnet;
        }
      }
    }),

    setCurrentTopologyId: (id) => set((state) => {
      state.currentTopologyId = id;
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
