import axios from 'axios';
import type { NetworkNode, NetworkLink } from '@octet/shared-types';
import { getAuthToken, setAuthToken } from './authToken';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface TopologyData {
  id?: string;
  name: string;
  description?: string;
  status: string;
  nodes: NetworkNode[];
  edges: NetworkLink[];
}

export interface TemplateSummary {
  id: string;
  name: string;
  description: string;
  tags: string[];
  abstractionLevel: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  role: string;
  accountTier: 'free' | 'pro' | 'enterprise';
}

export interface AuthResponse {
  accessToken: string;
  tokenType: 'bearer';
  user: CurrentUser;
}

export interface ProbeRequest {
  sourceNodeId: string;
  targetIp: string;
  probeType: 'ping' | 'traceroute';
}

export interface FaultRequest {
  linkId: string;
  faultType: 'link-down' | 'high-latency' | 'packet-loss';
}

export interface TopologyExportData {
  exportFormat: 'octet-v1';
  topologyId?: string;
  name: string;
  description?: string;
  abstractionLevel: string;
  status: string;
  engineTopoId?: string;
  exportedAt?: string;
  nodes: NetworkNode[];
  edges: NetworkLink[];
}

export const api = {
  async register(email: string, password: string): Promise<AuthResponse> {
    const response = await apiClient.post('/auth/register', { email, password });
    setAuthToken(response.data.accessToken);
    return response.data;
  },

  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await apiClient.post('/auth/login', { email, password });
    setAuthToken(response.data.accessToken);
    return response.data;
  },

  async getCurrentUser(): Promise<CurrentUser> {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  async createTopology(data: TopologyData) {
    const response = await apiClient.post('/topology/', data);
    return response.data;
  },

  async updateTopology(id: string, data: Partial<TopologyData>) {
    const response = await apiClient.put(`/topology/${id}`, data);
    return response.data;
  },

  async getTopologies() {
    const response = await apiClient.get('/topology/');
    return response.data;
  },

  async getTopology(id: string) {
    const response = await apiClient.get(`/topology/${id}`);
    return response.data;
  },

  async startSimulation(topologyId: string) {
    const response = await apiClient.post(`/topology/${topologyId}/start`);
    return response.data;
  },

  async stopSimulation(topologyId: string) {
    const response = await apiClient.post(`/topology/${topologyId}/stop`);
    return response.data;
  },

  async getTemplates(): Promise<TemplateSummary[]> {
    const response = await apiClient.get('/templates/');
    return response.data;
  },

  async instantiateTemplate(templateId: string): Promise<TopologyData> {
    const response = await apiClient.post(`/templates/${templateId}/instantiate`);
    return response.data;
  },

  async runProbe(topologyId: string, data: ProbeRequest) {
    const response = await apiClient.post(`/topology/${topologyId}/probe`, data);
    return response.data;
  },

  async injectFault(topologyId: string, data: FaultRequest) {
    const response = await apiClient.post(`/topology/${topologyId}/fault`, data);
    return response.data;
  },

  async exportTopology(topologyId: string): Promise<TopologyExportData> {
    const response = await apiClient.get(`/topology/${topologyId}/export`);
    return response.data;
  },

  async exportTopologyReport(topologyId: string): Promise<string> {
    const response = await apiClient.get(`/topology/${topologyId}/report.md`, {
      responseType: 'text',
    });
    return response.data;
  },

  async exportTopologyReportPdf(topologyId: string): Promise<BlobPart> {
    const response = await apiClient.get(`/topology/${topologyId}/report.pdf`, {
      responseType: 'arraybuffer',
    });
    return response.data;
  },

  async exportTopologyReportDoc(topologyId: string): Promise<BlobPart> {
    const response = await apiClient.get(`/topology/${topologyId}/report.doc`, {
      responseType: 'arraybuffer',
    });
    return response.data;
  },

  async importTopology(data: TopologyExportData) {
    const response = await apiClient.post('/topology/import', data);
    return response.data;
  }
};
