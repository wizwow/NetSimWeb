import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { NetworkNode, NetworkLink } from '@netsimflow/shared-types';
import { applyNodeChanges, applyEdgeChanges, addEdge } from '@xyflow/react';
import type { Node, Edge, Connection, NodeChange, EdgeChange } from '@xyflow/react';
import { v4 as uuidv4 } from 'uuid';
import { api } from '../services/api';

export type ReactFlowNode = Node<NetworkNode>;
export type ReactFlowEdge = Edge<NetworkLink>;

interface TopologyState {
  currentTopologyId: string | null;
  nodes: ReactFlowNode[];
  edges: ReactFlowEdge[];
  selectedNodeIds: string[];
  selectedEdgeIds: string[];
  logs: { id: string; timestamp: string; level: 'info' | 'warn' | 'error'; message: string; source?: string }[];
  
  // Actions
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  addNode: (node: NetworkNode) => void;
  removeNodes: (nodeIds: string[]) => void;
  updateNodeStatus: (nodeId: string, status: NetworkNode['runtimeState']['status']) => void;
  updateNode: (nodeId: string, updates: Partial<NetworkNode>) => void;
  updateEdge: (edgeId: string, updates: Partial<NetworkLink>) => void;
  
  // Async actions
  saveTopology: () => Promise<void>;
  loadLatestTopology: () => Promise<void>;
  triggerAutoIp: () => Promise<void>;
  startSimulation: () => Promise<void>;
  stopSimulation: () => Promise<void>;
  addLog: (message: string, level?: 'info' | 'warn' | 'error', source?: string) => void;
  clearLogs: () => void;
}

export const useTopologyStore = create<TopologyState>()(
  immer((set, get) => ({
    currentTopologyId: null,
    nodes: [],
    edges: [],
    selectedNodeIds: [],
    selectedEdgeIds: [],
    logs: [],

    onNodesChange: (changes) => {
      set((state) => {
        state.nodes = applyNodeChanges(changes, state.nodes as any) as any;
      });
    },

    onEdgesChange: (changes) => {
      set((state) => {
        state.edges = applyEdgeChanges(changes, state.edges as any) as any;
      });
    },

    onConnect: (connection) => {
      set((state) => {
        const newEdge: ReactFlowEdge = {
          id: `edge-${uuidv4()}`,
          source: connection.source!,
          target: connection.target!,
          sourceHandle: connection.sourceHandle,
          targetHandle: connection.targetHandle,
          type: 'simulatedEdge', // We will create this custom edge later
          data: {
            id: `lnk-${uuidv4()}`,
            sourceNodeId: connection.source!,
            targetNodeId: connection.target!,
            sourcePort: connection.sourceHandle || 'default',
            targetPort: connection.targetHandle || 'default',
            linkType: 'ethernet'
          }
        };
        state.edges = addEdge(newEdge, state.edges as any) as any;
      });
      get().triggerAutoIp();
    },

    addNode: (networkNode) => {
      const newNode: ReactFlowNode = {
        id: networkNode.id,
        type: networkNode.baseType, // 'router', 'switch', etc.
        position: networkNode.position,
        data: networkNode
      };
      set((state) => {
        state.nodes.push(newNode);
      });
    },

    removeNodes: (nodeIds) => {
      set((state) => {
        state.nodes = state.nodes.filter(n => !nodeIds.includes(n.id));
        state.edges = state.edges.filter(e => !nodeIds.includes(e.source) && !nodeIds.includes(e.target));
      });
    },

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
        // Se cambia la label, aggiorniamo anche la label del nodo React Flow
        if (updates.label) node.data.label = updates.label;
      }
    }),

    updateEdge: (edgeId, updates) => set((state) => {
      const edge = state.edges.find(e => e.id === edgeId);
      if (edge) {
        edge.data = { ...edge.data, ...updates };
        // Se cambia la subnet, aggiorniamo la label dell'edge
        if (updates.ipConfig?.subnet) {
          edge.label = updates.ipConfig.subnet;
        }
      }
    }),

    saveTopology: async () => {
      const state = get();
      // Mappiamo i nodi e gli edge dal formato ReactFlow al nostro formato custom
      const nodesToSave = state.nodes.map(n => ({
        ...n.data,
        position: n.position
      }));
      const edgesToSave = state.edges.map(e => e.data as NetworkLink);

      try {
        if (state.currentTopologyId) {
          await api.updateTopology(state.currentTopologyId, {
            name: 'My Saved Topology', // Mettiamo un nome fisso temporaneo
            nodes: nodesToSave,
            edges: edgesToSave
          });
        } else {
          const newTopo = await api.createTopology({
            name: 'New Topology',
            status: 'draft',
            nodes: nodesToSave,
            edges: edgesToSave
          });
          set(s => { s.currentTopologyId = newTopo.id; });
        }
        alert('Topology saved successfully!');
      } catch (err) {
        console.error("Error saving topology", err);
        alert('Failed to save topology');
      }
    },

    triggerAutoIp: async () => {
      const state = get();
      const nodesToSave = state.nodes.map(n => ({
        ...n.data,
        position: n.position
      }));
      const edgesToSave = state.edges.map(e => e.data as NetworkLink);

      try {
        const result = await api.autoAssignIps({
          name: 'Temp',
          status: 'draft',
          nodes: nodesToSave,
          edges: edgesToSave
        });
        
        set(s => {
          s.nodes = result.nodes.map((n: NetworkNode) => ({
            id: n.id,
            type: n.baseType,
            position: n.position,
            data: n
          }));
          s.edges = result.edges.map((e: NetworkLink) => ({
            id: e.id,
            source: e.sourceNodeId,
            target: e.targetNodeId,
            sourceHandle: e.sourcePort,
            targetHandle: e.targetPort,
            label: e.ipConfig?.subnet || '',
            data: e
          }));
        });
      } catch (err) {
        console.error("AutoIP failed", err);
      }
    },

    loadLatestTopology: async () => {
      try {
        const topos = await api.getTopologies();
        if (topos.length > 0) {
          const latest = topos[0]; // API returns ORDER BY created_at DESC
          set(state => {
            state.currentTopologyId = latest.id;
            state.nodes = latest.nodes.map((n: NetworkNode) => ({
              id: n.id,
              type: n.baseType,
              position: n.position,
              data: n
            }));
            state.edges = latest.edges.map((e: NetworkLink) => ({
              id: e.id,
              source: e.sourceNodeId,
              target: e.targetNodeId,
              sourceHandle: e.sourcePort,
              targetHandle: e.targetPort,
              label: e.ipConfig?.subnet || '',
              data: e
            }));
          });
          alert('Topology loaded!');
        } else {
          alert('No topologies found in database.');
        }
      } catch (err) {
        console.error("Error loading topology", err);
        alert('Failed to load topology');
      }
    },

    startSimulation: async () => {
      const { currentTopologyId } = get();
      if (!currentTopologyId) {
        alert("Salva la topologia prima di avviarla!");
        return;
      }
      try {
        await api.startSimulation(currentTopologyId);
        // Not: lo stato dei nodi verrà aggiornato o dalla risposta o dai WS
        set(state => {
          state.nodes.forEach(n => {
            if (!n.data.runtimeState) n.data.runtimeState = { status: 'booting' };
            n.data.runtimeState.status = 'running';
          });
        });
      } catch (err) {
        console.error("Start simulation failed", err);
      }
    },

    stopSimulation: async () => {
      const { currentTopologyId } = get();
      if (!currentTopologyId) return;
      try {
        await api.stopSimulation(currentTopologyId);
        set(state => {
          state.nodes.forEach(n => {
            if (n.data.runtimeState) n.data.runtimeState.status = 'stopped';
          });
        });
      } catch (err) {
        console.error("Stop simulation failed", err);
      }
    },

    addLog: (message, level = 'info', source) => set((state) => {
      state.logs.push({
        id: uuidv4(),
        timestamp: new Date().toLocaleTimeString(),
        level,
        message,
        source
      });
      // Mantieni solo gli ultimi 100 log
      if (state.logs.length > 100) state.logs.shift();
    }),

    clearLogs: () => set((state) => {
      state.logs = [];
    })
  }))
);
