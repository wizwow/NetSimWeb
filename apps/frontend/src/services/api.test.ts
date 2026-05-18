import { describe, expect, it, vi } from 'vitest';

vi.mock('axios', () => {
  const client = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  };
  return {
    default: {
      create: vi.fn(() => client),
    },
  };
});

const { default: axios } = await import('axios');
const { api } = await import('./api');
import type { TopologyExportData } from './api';

const client = vi.mocked(axios.create).mock.results[0].value as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  put: ReturnType<typeof vi.fn>;
};

describe('api service', () => {
  it('calls export, report, and import topology endpoints', async () => {
    client.get.mockResolvedValueOnce({ data: { exportFormat: 'netsimflow-v1' } });
    client.get.mockResolvedValueOnce({ data: '# Report' });
    client.post.mockResolvedValueOnce({ data: { id: 'topo-1' } });

    await api.exportTopology('topo-1');
    await api.exportTopologyReport('topo-1');
    const importPayload: TopologyExportData = {
      exportFormat: 'netsimflow-v1',
      name: 'Imported',
      abstractionLevel: 'logical',
      status: 'draft',
      nodes: [],
      edges: [],
    };
    await api.importTopology(importPayload);

    expect(client.get).toHaveBeenCalledWith('/topology/topo-1/export');
    expect(client.get).toHaveBeenCalledWith('/topology/topo-1/report.md', {
      responseType: 'text',
    });
    expect(client.post).toHaveBeenCalledWith('/topology/import', importPayload);
  });
});
