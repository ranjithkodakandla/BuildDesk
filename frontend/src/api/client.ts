import axios from 'axios';
import { useAuthStore } from '../store/authStore';

// In development the Vite proxy handles /api/* → backend.
// In production builds, VITE_API_BASE_URL must be set.
const BASE_URL =
  import.meta.env.DEV
    ? ''  // Use relative URL; Vite dev proxy handles it
    : (import.meta.env.VITE_API_BASE_URL || '');

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
