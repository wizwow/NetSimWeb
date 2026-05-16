import { useCallback } from 'react';
import type { NetworkNode, NetworkLink } from '@netsimflow/shared-types';
import { useTopologyStore } from '../store';
import { useSimulationStore } from '../store/simulation.slice';
import { api } from '../services/api';

/**
 * Hook that owns all topology-related API side effects.
 * Components call these functions; the hook writes results to the stores.
 */
export const useTopology = () => {
  const {
    nodes, edges, currentTopologyId,
    setCurrentTopologyId, replaceGraph, setAllNodesStatus,
  } = useTopologyStore();
  const addLog = useSimulationStore(s => s.addLog);

  const saveTopology = useCallback(async () => {
    const nodesToSave = nodes.map(n => ({ ...n.data, position: n.position }));
    const edgesToSave = edges.map(e => e.data as NetworkLink);

    try {
      if (currentTopologyId) {
        await api.updateTopology(currentTopologyId, {
          name: 'My Saved Topology',
          nodes: nodesToSave,
          edges: edgesToSave,
        });
      } else {
        const newTopo = await api.createTopology({
          name: 'New Topology',
          status: 'draft',
          nodes: nodesToSave,
          edges: edgesToSave,
        });
        setCurrentTopologyId(newTopo.id);
      }
      addLog('Topology saved successfully', 'info', 'system');
    } catch (err) {
      console.error('Error saving topology', err);
      addLog('Failed to save topology', 'error', 'system');
    }
  }, [nodes, edges, currentTopologyId, setCurrentTopologyId, addLog]);

  const loadLatestTopology = useCallback(async () => {
    try {
      const topos = await api.getTopologies();
      if (topos.length > 0) {
        const latest = topos[0];
        setCurrentTopologyId(latest.id);
        replaceGraph(latest.nodes as NetworkNode[], latest.edges as NetworkLink[]);
        addLog(`Topology "${latest.name}" loaded`, 'info', 'system');
      } else {
        addLog('No topologies found in database', 'warn', 'system');
      }
    } catch (err) {
      console.error('Error loading topology', err);
      addLog('Failed to load topology', 'error', 'system');
    }
  }, [setCurrentTopologyId, replaceGraph, addLog]);

  const triggerAutoIp = useCallback(async () => {
    const nodesToSave = nodes.map(n => ({ ...n.data, position: n.position }));
    const edgesToSave = edges.map(e => e.data as NetworkLink);

    try {
      const result = await api.autoAssignIps({
        name: 'Temp',
        status: 'draft',
        nodes: nodesToSave,
        edges: edgesToSave,
      });
      replaceGraph(result.nodes as NetworkNode[], result.edges as NetworkLink[]);
    } catch (err) {
      console.error('AutoIP failed', err);
    }
  }, [nodes, edges, replaceGraph]);

  const startSimulation = useCallback(async () => {
    if (!currentTopologyId) {
      addLog('Save the topology before starting the simulation', 'warn', 'system');
      return;
    }
    try {
      await api.startSimulation(currentTopologyId);
      setAllNodesStatus('running');
    } catch (err) {
      console.error('Start simulation failed', err);
    }
  }, [currentTopologyId, setAllNodesStatus, addLog]);

  const stopSimulation = useCallback(async () => {
    if (!currentTopologyId) return;
    try {
      await api.stopSimulation(currentTopologyId);
      setAllNodesStatus('stopped');
    } catch (err) {
      console.error('Stop simulation failed', err);
    }
  }, [currentTopologyId, setAllNodesStatus]);

  return {
    saveTopology,
    loadLatestTopology,
    triggerAutoIp,
    startSimulation,
    stopSimulation,
  };
};
