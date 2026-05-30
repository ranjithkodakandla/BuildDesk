import { apiClient } from './client';

export interface RegisterRequest {
  workspace_name: string;
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
  register: (body: RegisterRequest) =>
    apiClient.post<TokenResponse>('/auth/register', body),

  login: (body: LoginRequest) =>
    apiClient.post<TokenResponse>('/auth/login', body),

  me: () => apiClient.get<UserProfile>('/auth/me'),
};

export const healthApi = {
  check: () => apiClient.get<HealthResponse>('/health'),
};
