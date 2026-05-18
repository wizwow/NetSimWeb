import { useCallback, useEffect, useState } from 'react';
import type { NetworkNode, NetworkLink } from '@netsimflow/shared-types';
import { useTopologyStore } from '../store';
import { useSimulationStore } from '../store/simulation.slice';
import { api, type TemplateSummary, type TopologyExportData } from '../services/api';
import { downloadJsonFile, downloadTextFile, exportFileName, reportFileName } from '../services/exportFile';

/**
 * Hook that owns all topology-related API side effects.
 * Components call these functions; the hook writes results to the stores.
 */
export const useTopology = () => {
  const {
    nodes, edges, currentTopologyId, currentTopologyName,
    setCurrentTopologyId, setCurrentTopologyName, replaceGraph, setAllNodesStatus, updateEdgeFault,
  } = useTopologyStore();
  const addLog = useSimulationStore(s => s.addLog);
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(true);
  const [templatesError, setTemplatesError] = useState<string | null>(null);

  const loadTemplates = useCallback(async () => {
    setTemplatesLoading(true);
    setTemplatesError(null);
    try {
      const loadedTemplates = await api.getTemplates();
      setTemplates(loadedTemplates);
      if (loadedTemplates.length === 0) {
        setTemplatesError('No topology templates are available');
      }
    } catch (err) {
      console.error('Template list load failed', err);
      setTemplatesError('Could not load topology templates');
      addLog('Could not load topology templates', 'error', 'template');
    } finally {
      setTemplatesLoading(false);
    }
  }, [addLog]);

  useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  const saveTopology = useCallback(async () => {
    const nodesToSave = nodes.map(n => ({ ...n.data, position: n.position }));
    const edgesToSave = edges.map(e => e.data as NetworkLink);

    try {
      if (currentTopologyId) {
        await api.updateTopology(currentTopologyId, {
          name: currentTopologyName,
          nodes: nodesToSave,
          edges: edgesToSave,
        });
      } else {
        const newTopo = await api.createTopology({
          name: currentTopologyName,
          status: 'draft',
          nodes: nodesToSave,
          edges: edgesToSave,
        });
        setCurrentTopologyId(newTopo.id);
        setCurrentTopologyName(newTopo.name);
      }
      addLog(`Topology "${currentTopologyName}" saved successfully`, 'info', 'system');
    } catch (err) {
      console.error('Error saving topology', err);
      addLog('Failed to save topology', 'error', 'system');
    }
  }, [nodes, edges, currentTopologyId, currentTopologyName, setCurrentTopologyId, setCurrentTopologyName, addLog]);

  const loadLatestTopology = useCallback(async () => {
    try {
      const topos = await api.getTopologies();
      if (topos.length > 0) {
        const latest = topos[0];
        setCurrentTopologyId(latest.id);
        setCurrentTopologyName(latest.name);
        replaceGraph(latest.nodes as NetworkNode[], latest.edges as NetworkLink[]);
        addLog(`Topology "${latest.name}" loaded`, 'info', 'system');
      } else {
        addLog('No topologies found in database', 'warn', 'system');
      }
    } catch (err) {
      console.error('Error loading topology', err);
      addLog('Failed to load topology', 'error', 'system');
    }
  }, [setCurrentTopologyId, setCurrentTopologyName, replaceGraph, addLog]);

  const triggerAutoIp = useCallback(async () => {
    if (nodes.length === 0 && edges.length === 0) {
      addLog('Add devices or load a template before running Auto-IP', 'warn', 'autoip');
      return;
    }

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
    if (!templateId) {
      addLog('Select a template before loading', 'warn', 'template');
      return;
    }

    try {
      const result = await api.instantiateTemplate(templateId);
      setCurrentTopologyId(null);
      setCurrentTopologyName(result.name);
      replaceGraph(result.nodes as NetworkNode[], result.edges as NetworkLink[]);
      addLog(`Template "${result.name}" loaded`, 'info', 'template');
    } catch (err) {
      console.error('Template load failed', err);
      addLog('Template load failed', 'error', 'template');
    }
  }, [setCurrentTopologyId, setCurrentTopologyName, replaceGraph, addLog]);

  const startSimulation = useCallback(async () => {
    if (!currentTopologyId) {
      addLog('Save the topology before starting the simulation', 'warn', 'system');
      return;
    }
    try {
      await api.startSimulation(currentTopologyId);
      setAllNodesStatus('running');
      addLog('Simulation started', 'info', 'engine');
    } catch (err) {
      console.error('Start simulation failed', err);
      addLog('Failed to start simulation', 'error', 'engine');
    }
  }, [currentTopologyId, setAllNodesStatus, addLog]);

  const stopSimulation = useCallback(async () => {
    if (!currentTopologyId) {
      addLog('Save the topology before stopping the simulation', 'warn', 'system');
      return;
    }
    try {
      await api.stopSimulation(currentTopologyId);
      setAllNodesStatus('stopped');
      addLog('Simulation stopped', 'info', 'engine');
    } catch (err) {
      console.error('Stop simulation failed', err);
      addLog('Failed to stop simulation', 'error', 'engine');
    }
  }, [currentTopologyId, setAllNodesStatus, addLog]);

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
      addLog(`Ping ${sourceNodeId} → ${targetIp}: ${result.output}`, result.success ? 'info' : 'error', 'probe');
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
      addLog(`Link fault injected on ${linkId}: link-down`, 'warn', 'fault');
    } catch (err) {
      console.error('Fault injection failed', err);
      addLog('Fault injection failed', 'error', 'fault');
    }
  }, [currentTopologyId, updateEdgeFault, addLog]);

  const exportTopology = useCallback(async () => {
    if (!currentTopologyId) {
      addLog('Save the topology before exporting JSON', 'warn', 'export');
      return;
    }

    try {
      const exportData = await api.exportTopology(currentTopologyId);
      downloadJsonFile(exportData, exportFileName(exportData.name));
      addLog(`Exported "${exportData.name}" as JSON`, 'info', 'export');
    } catch (err) {
      console.error('Export failed', err);
      addLog('JSON export failed', 'error', 'export');
    }
  }, [currentTopologyId, addLog]);

  const importTopology = useCallback(async (file: File) => {
    try {
      const raw = await file.text();
      const parsed = JSON.parse(raw) as TopologyExportData;
      if (parsed.exportFormat !== 'netsimflow-v1') {
        addLog('Unsupported topology export format', 'error', 'import');
        return;
      }

      const imported = await api.importTopology(parsed);
      setCurrentTopologyId(imported.id);
      setCurrentTopologyName(imported.name);
      replaceGraph(imported.nodes as NetworkNode[], imported.edges as NetworkLink[]);
      addLog(`Imported "${imported.name}" from JSON`, 'info', 'import');
    } catch (err) {
      console.error('Import failed', err);
      addLog('JSON import failed', 'error', 'import');
    }
  }, [setCurrentTopologyId, setCurrentTopologyName, replaceGraph, addLog]);

  const exportReport = useCallback(async () => {
    if (!currentTopologyId) {
      addLog('Save the topology before exporting a report', 'warn', 'export');
      return;
    }

    try {
      const markdown = await api.exportTopologyReport(currentTopologyId);
      downloadTextFile(markdown, reportFileName(currentTopologyName), 'text/markdown');
      addLog(`Exported "${currentTopologyName}" report as Markdown`, 'info', 'export');
    } catch (err) {
      console.error('Report export failed', err);
      addLog('Markdown report export failed', 'error', 'export');
    }
  }, [currentTopologyId, currentTopologyName, addLog]);

  return {
    templates,
    templatesLoading,
    templatesError,
    loadTemplates,
    currentTopologyName,
    setCurrentTopologyName,
    saveTopology,
    loadLatestTopology,
    triggerAutoIp,
    loadTemplate,
    startSimulation,
    stopSimulation,
    runProbe,
    injectFault,
    exportTopology,
    exportReport,
    importTopology,
  };
};
