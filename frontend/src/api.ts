import axios from 'axios';

const BASE_URL = 'http://localhost:8000';

const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('api_key');
  if (apiKey) config.headers['x-api-key'] = apiKey;
  return config;
});

export const registerOrg = (name: string) =>
  api.post('/api/auth/register', { name });

export const listAgents = () =>
  api.get('/api/agents/list');

export const registerAgent = (name: string, capabilities: string[]) =>
  api.post('/api/agents/register', { name, capabilities });

export const getAgent = (id: string) =>
  api.get(`/api/agents/${id}`);

export const logBehavior = (agentId: string, action: string, payload: object) =>
  api.post(`/api/agents/${agentId}/behavior`, { action, payload });

export const getAuditTrail = (agentId: string) =>
  api.get(`/api/agents/${agentId}/audit-trail`);

export const verifyInteraction = (data: object) =>
  api.post('/api/agents/verify-interaction', data);

export default api;