import { describe, expect, it, vi } from 'vitest';

vi.mock('axios', () => {
  const client = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    interceptors: {
      request: {
        use: vi.fn(),
      },
    },
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
  interceptors: {
    request: {
      use: ReturnType<typeof vi.fn>;
    };
  };
};

describe('api service', () => {
  it('stores login token and attaches it to requests', async () => {
    const requestInterceptor = client.interceptors.request.use.mock.calls[0][0];
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue('stored-token');
    const config = requestInterceptor({ headers: {} });
    expect(config.headers.Authorization).toBe('Bearer stored-token');

    const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => undefined);
    client.post.mockResolvedValueOnce({
      data: {
        accessToken: 'new-token',
        tokenType: 'bearer',
        user: {
          id: 'user-1',
          email: 'teacher@example.com',
          role: 'designer',
          accountTier: 'free',
        },
      },
    });

    await api.login('teacher@example.com', 'valid-pass');

    expect(client.post).toHaveBeenCalledWith('/auth/login', {
      email: 'teacher@example.com',
      password: 'valid-pass',
    });
    expect(setItem).toHaveBeenCalledWith('netsimflow.authToken', 'new-token');
  });

  it('calls export, report, and import topology endpoints', async () => {
    client.get.mockResolvedValueOnce({ data: { exportFormat: 'netsimflow-v1' } });
    client.get.mockResolvedValueOnce({ data: '# Report' });
    client.get.mockResolvedValueOnce({ data: new ArrayBuffer(8) });
    client.get.mockResolvedValueOnce({ data: new ArrayBuffer(8) });
    client.post.mockResolvedValueOnce({ data: { id: 'topo-1' } });

    await api.exportTopology('topo-1');
    await api.exportTopologyReport('topo-1');
    await api.exportTopologyReportPdf('topo-1');
    await api.exportTopologyReportDoc('topo-1');
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
    expect(client.get).toHaveBeenCalledWith('/topology/topo-1/report.pdf', {
      responseType: 'arraybuffer',
    });
    expect(client.get).toHaveBeenCalledWith('/topology/topo-1/report.doc', {
      responseType: 'arraybuffer',
    });
    expect(client.post).toHaveBeenCalledWith('/topology/import', importPayload);
  });
});
