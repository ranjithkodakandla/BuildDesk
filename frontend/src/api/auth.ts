import { apiClient } from './client';

export interface RegisterRequest {
  email: string;
  password: string;
  role?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  tenant_id: string;
  role: string;
  email: string;
}

export interface UserProfile {
  user_id: string;
  tenant_id: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  database: string;
  tenant_mode: boolean;
}

export const authApi = {
  register: (tenantId: string, body: RegisterRequest) =>
    apiClient.post<TokenResponse>('/api/v1/auth/register', body, {
      headers: { 'X-Tenant-ID': tenantId },
    }),

  login: (tenantId: string, body: LoginRequest) =>
    apiClient.post<TokenResponse>('/api/v1/auth/login', body, {
      headers: { 'X-Tenant-ID': tenantId },
    }),

  me: () => apiClient.get<UserProfile>('/api/v1/auth/me'),
};

export const healthApi = {
  check: () => apiClient.get<HealthResponse>('/api/v1/health'),
};
