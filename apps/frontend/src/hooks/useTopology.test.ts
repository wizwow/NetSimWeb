import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { NetworkLink, NetworkNode } from '@netsimflow/shared-types';
import type { TopologyData, TopologyExportData } from '../services/api';
import { useTopologyStore } from '../store';
import { useSimulationStore } from '../store/simulation.slice';

vi.mock('../services/api', () => ({
  api: {
    createTopology: vi.fn(),
    updateTopology: vi.fn(),
    getTopologies: vi.fn(),
    autoAssignIps: vi.fn(),
    startSimulation: vi.fn(),
    stopSimulation: vi.fn(),
    getTemplates: vi.fn(),
    instantiateTemplate: vi.fn(),
    runProbe: vi.fn(),
    injectFault: vi.fn(),
    exportTopology: vi.fn(),
    importTopology: vi.fn(),
  },
}));

vi.mock('../services/exportFile', () => ({
  downloadJsonFile: vi.fn(),
  exportFileName: vi.fn((name: string) => `${name}.netsimflow.json`),
}));

const { api } = await import('../services/api');
const { downloadJsonFile, exportFileName } = await import('../services/exportFile');
const { useTopology } = await import('./useTopology');

const mockedApi = vi.mocked(api);
const mockedDownloadJsonFile = vi.mocked(downloadJsonFile);
const mockedExportFileName = vi.mocked(exportFileName);

const nodeR1: NetworkNode = {
  id: 'r1',
  label: 'R1',
  position: { x: 0, y: 0 },
  baseType: 'router',
  tags: [],
};

const nodeR2: NetworkNode = {
  id: 'r2',
  label: 'R2',
  position: { x: 200, y: 0 },
  baseType: 'router',
  tags: [],
};

const edgeR1R2: NetworkLink = {
  id: 'lnk-r1-r2',
  sourceNodeId: 'r1',
  sourcePort: 'GigabitEthernet0/0',
  targetNodeId: 'r2',
  targetPort: 'GigabitEthernet0/0',
  linkType: 'ethernet',
  ipConfig: {
    subnet: '10.0.1.0/30',
    sourceIp: '10.0.1.1',
    targetIp: '10.0.1.2',
  },
};

const templateSummary = {
  id: 'ospf-3-sites',
  name: 'OSPF 3 Sites',
  description: 'Three site OSPF template',
  tags: ['ospf'],
  abstractionLevel: 'logical',
};

function resetStores() {
  useTopologyStore.setState({
    currentTopologyId: null,
    currentTopologyName: 'New Topology',
    nodes: [],
    edges: [],
    selectedNodeIds: [],
    selectedEdgeIds: [],
  });
  useSimulationStore.setState({
    status: 'idle',
    logs: [],
    activeProbes: [],
  });
}

function seedGraph(nodes: NetworkNode[] = [nodeR1, nodeR2], edges: NetworkLink[] = [edgeR1R2]) {
  act(() => {
    useTopologyStore.getState().replaceGraph(nodes, edges);
  });
}

function latestLog() {
  const logs = useSimulationStore.getState().logs;
  return logs[logs.length - 1];
}

function topologyResponse(overrides: Partial<TopologyData> = {}): TopologyData {
  return {
    id: 'topo-1',
    name: 'Saved Topology',
    status: 'draft',
    nodes: [nodeR1, nodeR2],
    edges: [edgeR1R2],
    ...overrides,
  };
}

function textFile(contents: string): File {
  return {
    text: vi.fn().mockResolvedValue(contents),
  } as unknown as File;
}

describe('useTopology', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    mockedApi.getTemplates.mockResolvedValue([templateSummary]);
    mockedExportFileName.mockImplementation((name: string | undefined) => `${name}.netsimflow.json`);
    resetStores();
  });

  it('loads template summaries and exposes empty/error states', async () => {
    const { result, unmount } = renderHook(() => useTopology());

    await waitFor(() => expect(result.current.templatesLoading).toBe(false));
    expect(result.current.templates).toEqual([templateSummary]);
    expect(result.current.templatesError).toBeNull();
    unmount();

    mockedApi.getTemplates.mockResolvedValueOnce([]);
    const empty = renderHook(() => useTopology());
    await waitFor(() => expect(empty.result.current.templatesLoading).toBe(false));
    expect(empty.result.current.templatesError).toBe('No topology templates are available');
    empty.unmount();

    mockedApi.getTemplates.mockRejectedValueOnce(new Error('offline'));
    const failed = renderHook(() => useTopology());
    await waitFor(() => expect(failed.result.current.templatesLoading).toBe(false));
    expect(failed.result.current.templatesError).toBe('Could not load topology templates');
    expect(latestLog().message).toBe('Could not load topology templates');
    failed.unmount();
  });

  it('saves a new topology and stores the returned id/name', async () => {
    seedGraph();
    useTopologyStore.getState().setCurrentTopologyName('Class Demo');
    mockedApi.createTopology.mockResolvedValue(topologyResponse({ id: 'topo-new', name: 'Class Demo' }));

    const { result } = renderHook(() => useTopology());
    await waitFor(() => expect(result.current.templatesLoading).toBe(false));

    await act(async () => {
      await result.current.saveTopology();
    });

    expect(mockedApi.createTopology).toHaveBeenCalledWith(expect.objectContaining({
      name: 'Class Demo',
      nodes: [nodeR1, nodeR2],
      edges: [edgeR1R2],
    }));
    expect(useTopologyStore.getState().currentTopologyId).toBe('topo-new');
    expect(useTopologyStore.getState().currentTopologyName).toBe('Class Demo');
    expect(latestLog().message).toBe('Topology "Class Demo" saved successfully');
  });

  it('loads the latest topology into the graph and name state', async () => {
    mockedApi.getTopologies.mockResolvedValue([
      topologyResponse({ id: 'latest', name: 'Latest Saved' }),
    ]);
    const { result } = renderHook(() => useTopology());
    await waitFor(() => expect(result.current.templatesLoading).toBe(false));

    await act(async () => {
      await result.current.loadLatestTopology();
    });

    const state = useTopologyStore.getState();
    expect(state.currentTopologyId).toBe('latest');
    expect(state.currentTopologyName).toBe('Latest Saved');
    expect(state.nodes.map(node => node.id)).toEqual(['r1', 'r2']);
    expect(state.edges.map(edge => edge.id)).toEqual(['lnk-r1-r2']);
    expect(latestLog().message).toBe('Topology "Latest Saved" loaded');
  });

  it('handles Auto-IP empty and success paths', async () => {
    const { result } = renderHook(() => useTopology());
    await waitFor(() => expect(result.current.templatesLoading).toBe(false));

    await act(async () => {
      await result.current.triggerAutoIp();
    });
    expect(mockedApi.autoAssignIps).not.toHaveBeenCalled();
    expect(latestLog().message).toBe('Add devices or load a template before running Auto-IP');

    const autoIpEdge = { ...edgeR1R2, ipConfig: { ...edgeR1R2.ipConfig!, subnet: '10.99.0.0/30' } };
    seedGraph([nodeR1, nodeR2], [{ ...edgeR1R2, ipConfig: undefined }]);
    mockedApi.autoAssignIps.mockResolvedValue(topologyResponse({ nodes: [nodeR1, nodeR2], edges: [autoIpEdge] }));

    await act(async () => {
      await result.current.triggerAutoIp();
    });

    expect(useTopologyStore.getState().edges[0].data?.ipConfig?.subnet).toBe('10.99.0.0/30');
    expect(latestLog().message).toBe('Auto-IP assignment completed');
  });

  it('guards start/stop before save and updates node status after save', async () => {
    seedGraph();
    const { result } = renderHook(() => useTopology());
    await waitFor(() => expect(result.current.templatesLoading).toBe(false));

    await act(async () => {
      await result.current.startSimulation();
    });
    expect(mockedApi.startSimulation).not.toHaveBeenCalled();
    expect(latestLog().message).toBe('Save the topology before starting the simulation');

    act(() => {
      useTopologyStore.getState().setCurrentTopologyId('topo-1');
    });
    mockedApi.startSimulation.mockResolvedValue({ status: 'ok' });
    mockedApi.stopSimulation.mockResolvedValue({ status: 'ok' });

    await act(async () => {
      await result.current.startSimulation();
    });
    expect(useTopologyStore.getState().nodes.every(node => node.data.runtimeState?.status === 'running')).toBe(true);

    await act(async () => {
      await result.current.stopSimulation();
    });
    expect(useTopologyStore.getState().nodes.every(node => node.data.runtimeState?.status === 'stopped')).toBe(true);
  });

  it('guards probe/fault before save and applies saved topology results', async () => {
    seedGraph();
    const { result } = renderHook(() => useTopology());
    await waitFor(() => expect(result.current.templatesLoading).toBe(false));

    await act(async () => {
      await result.current.runProbe('r1', '10.0.1.2');
    });
    expect(mockedApi.runProbe).not.toHaveBeenCalled();
    expect(latestLog().message).toBe('Save the topology before running a probe');

    await act(async () => {
      await result.current.injectFault('lnk-r1-r2');
    });
    expect(mockedApi.injectFault).not.toHaveBeenCalled();
    expect(latestLog().message).toBe('Save the topology before injecting a fault');

    act(() => {
      useTopologyStore.getState().setCurrentTopologyId('topo-1');
    });
    mockedApi.runProbe.mockResolvedValue({ success: true, output: 'Reply from 10.0.1.2: 3ms' });
    mockedApi.injectFault.mockResolvedValue({ status: 'ok' });

    await act(async () => {
      await result.current.runProbe('r1', '10.0.1.2');
    });
    expect(latestLog().message).toBe('Ping r1 → 10.0.1.2: Reply from 10.0.1.2: 3ms');

    await act(async () => {
      await result.current.injectFault('lnk-r1-r2');
    });
    expect(useTopologyStore.getState().edges[0].data?.faultState?.active).toBe(true);
    expect(latestLog().message).toBe('Link fault injected on lnk-r1-r2: link-down');
  });

  it('exports only saved topologies and downloads JSON with a friendly filename', async () => {
    const exportData: TopologyExportData = {
      exportFormat: 'netsimflow-v1',
      topologyId: 'topo-1',
      name: 'Class Demo',
      abstractionLevel: 'logical',
      status: 'draft',
      nodes: [nodeR1, nodeR2],
      edges: [edgeR1R2],
    };
    mockedApi.exportTopology.mockResolvedValue(exportData);
    const { result } = renderHook(() => useTopology());
    await waitFor(() => expect(result.current.templatesLoading).toBe(false));

    await act(async () => {
      await result.current.exportTopology();
    });
    expect(mockedApi.exportTopology).not.toHaveBeenCalled();
    expect(latestLog().message).toBe('Save the topology before exporting JSON');

    act(() => {
      useTopologyStore.getState().setCurrentTopologyId('topo-1');
    });

    await act(async () => {
      await result.current.exportTopology();
    });

    expect(mockedApi.exportTopology).toHaveBeenCalledWith('topo-1');
    expect(mockedExportFileName).toHaveBeenCalledWith('Class Demo');
    expect(mockedDownloadJsonFile).toHaveBeenCalledWith(exportData, 'Class Demo.netsimflow.json');
    expect(latestLog().message).toBe('Exported "Class Demo" as JSON');
  });

  it('imports valid exported topology and rejects invalid files', async () => {
    const { result } = renderHook(() => useTopology());
    await waitFor(() => expect(result.current.templatesLoading).toBe(false));

    await act(async () => {
      await result.current.importTopology(textFile('{"exportFormat":"old"}'));
    });
    expect(mockedApi.importTopology).not.toHaveBeenCalled();
    expect(latestLog().message).toBe('Unsupported topology export format');

    await act(async () => {
      await result.current.importTopology(textFile('not json'));
    });
    expect(latestLog().message).toBe('JSON import failed');

    const validExport: TopologyExportData = {
      exportFormat: 'netsimflow-v1',
      name: 'Imported Demo',
      abstractionLevel: 'logical',
      status: 'draft',
      nodes: [nodeR1, nodeR2],
      edges: [edgeR1R2],
    };
    mockedApi.importTopology.mockResolvedValue(topologyResponse({
      id: 'imported-topo',
      name: 'Imported Demo',
      nodes: [nodeR1, nodeR2],
      edges: [edgeR1R2],
    }));

    await act(async () => {
      await result.current.importTopology(textFile(JSON.stringify(validExport)));
    });

    const state = useTopologyStore.getState();
    expect(mockedApi.importTopology).toHaveBeenCalledWith(validExport);
    expect(state.currentTopologyId).toBe('imported-topo');
    expect(state.currentTopologyName).toBe('Imported Demo');
    expect(state.nodes.map(node => node.id)).toEqual(['r1', 'r2']);
    expect(state.edges.map(edge => edge.id)).toEqual(['lnk-r1-r2']);
    expect(latestLog().message).toBe('Imported "Imported Demo" from JSON');
  });
});
