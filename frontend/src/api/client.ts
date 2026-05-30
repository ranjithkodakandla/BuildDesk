import axios from 'axios';
import { useAuthStore } from '../store/authStore';

// Backend mounts all routes under /api/v1.
const PRODUCTION_HOST =
  'https://builddesk-api-149130710868.us-central1.run.app';

function resolveApiBaseUrl(): string {
  if (import.meta.env.DEV) {
    return '/api/v1';
  }
  const host = (import.meta.env.VITE_API_BASE_URL || PRODUCTION_HOST).replace(/\/$/, '');
  return host.endsWith('/api/v1') ? host : `${host}/api/v1`;
}

export const API_BASE_URL = resolveApiBaseUrl();

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Inject Bearer token on every request
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Global 401 handler — clear auth state
apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  }
);

export default apiClient;
export const api = apiClient;
