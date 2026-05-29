import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const DEFAULT_API_HOST = 'https://builddesk-api-149130710868.us-central1.run.app';

/**
 * Resolve the /api/v1 base URL.
 * - Dev: `/api/v1` (Vite proxies `/api` → backend)
 * - Prod: `VITE_API_BASE_URL` + `/api/v1` when not already suffixed
 */
export function resolveApiV1Base(): string {
  if (import.meta.env.MODE === 'test') {
    return 'http://localhost:8000/api/v1';
  }
  if (import.meta.env.DEV) {
    return '/api/v1';
  }
  const host = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_HOST).replace(/\/$/, '');
  return host.endsWith('/api/v1') ? host : `${host}/api/v1`;
}

export const apiClient = axios.create({
  baseURL: resolveApiV1Base(),
  headers: { 'Content-Type': 'application/json' },
});

// Inject Bearer token on every request
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const tenantId = useAuthStore.getState().tenantId;
  if (tenantId && !config.headers['X-Tenant-ID']) {
    config.headers['X-Tenant-ID'] = tenantId;
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
