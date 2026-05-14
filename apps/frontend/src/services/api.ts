import axios from 'axios';
import type { NetworkNode, NetworkLink } from '@netsimflow/shared-types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface TopologyData {
  id?: string;
  name: string;
  description?: string;
  status: string;
  nodes: NetworkNode[];
  edges: NetworkLink[];
}

export const api = {
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

  async autoAssignIps(data: TopologyData) {
    const response = await apiClient.post('/topology/autoip', data);
    return response.data;
  }
};
