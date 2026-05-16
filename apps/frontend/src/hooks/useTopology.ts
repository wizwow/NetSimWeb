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
    setCurrentTopologyId, replaceGraph, setAllNodesStatus, updateEdgeFault,
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
      addLog('Auto-IP assignment completed', 'info', 'autoip');
    } catch (err) {
      console.error('AutoIP failed', err);
      addLog('Auto-IP assignment failed', 'error', 'autoip');
    }
  }, [nodes, edges, replaceGraph, addLog]);

  const loadTemplate = useCallback(async (templateId: string) => {
    try {
      const result = await api.instantiateTemplate(templateId);
      setCurrentTopologyId(null);
      replaceGraph(result.nodes as NetworkNode[], result.edges as NetworkLink[]);
      addLog(`Template "${result.name}" loaded`, 'info', 'template');
    } catch (err) {
      console.error('Template load failed', err);
      addLog('Template load failed', 'error', 'template');
    }
  }, [setCurrentTopologyId, replaceGraph, addLog]);

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

  const runProbe = useCallback(async (sourceNodeId: string, targetIp: string) => {
    if (!currentTopologyId) {
      addLog('Save the topology before running a probe', 'warn', 'probe');
      return;
    }
    try {
      const result = await api.runProbe(currentTopologyId, {
        sourceNodeId,
        targetIp,
        probeType: 'ping',
      });
      addLog(result.output, result.success ? 'info' : 'error', 'probe');
    } catch (err) {
      console.error('Probe failed', err);
      addLog('Probe failed', 'error', 'probe');
    }
  }, [currentTopologyId, addLog]);

  const injectFault = useCallback(async (linkId: string) => {
    if (!currentTopologyId) {
      addLog('Save the topology before injecting a fault', 'warn', 'fault');
      return;
    }
    try {
      await api.injectFault(currentTopologyId, {
        linkId,
        faultType: 'link-down',
      });
      updateEdgeFault(linkId, {
        active: true,
        type: 'link-down',
        triggeredAt: new Date().toISOString(),
      });
      addLog(`Link fault injected on ${linkId}`, 'warn', 'fault');
    } catch (err) {
      console.error('Fault injection failed', err);
      addLog('Fault injection failed', 'error', 'fault');
    }
  }, [currentTopologyId, updateEdgeFault, addLog]);

  return {
    saveTopology,
    loadLatestTopology,
    triggerAutoIp,
    loadTemplate,
    startSimulation,
    stopSimulation,
    runProbe,
    injectFault,
  };
};
