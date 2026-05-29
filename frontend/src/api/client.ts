import axios from 'axios';
import { useAuthStore } from '../store/authStore';

// In development the Vite proxy handles /api/* → backend.
// In production builds, VITE_API_BASE_URL must be set.
const PRODUCTION_API =
  'https://builddesk-api-149130710868.us-central1.run.app';

const BASE_URL = import.meta.env.DEV
  ? '' // Vite dev proxy handles /api
  : (import.meta.env.VITE_API_BASE_URL || PRODUCTION_API);

export const apiClient = axios.create({
  baseURL: BASE_URL,
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
