import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '';

const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const researchApi = {
  submitJob: async (query) => {
    const response = await apiClient.post('/jobs/async-research', { query });
    return response.data;
  },
  
  checkStatus: async (jobId) => {
    const response = await apiClient.get(`/jobs/research-status/${jobId}`);
    return response.data;
  },
  
  getResult: async (jobId) => {
    const response = await apiClient.get(`/jobs/research-result/${jobId}`);
    return response.data;
  },
  
  cancelJob: async (jobId) => {
    const response = await apiClient.post(`/jobs/research-cancel/${jobId}`);
    return response.data;
  }
};
