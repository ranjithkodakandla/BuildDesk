import { create } from 'zustand';
import { authApi, type UserProfile } from '../api/auth';

const TOKEN_KEY = 'bd_token';
const TENANT_KEY = 'bd_tenant_id';

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  tenantId: string | null;
  loading: boolean;
  error: string | null;

  login: (token: string, user: UserProfile) => void;
  logout: () => void;
  setError: (msg: string | null) => void;
  bootstrap: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem(TOKEN_KEY),
  user: null,
  tenantId: localStorage.getItem(TENANT_KEY),
  loading: false,
  error: null,

  login: (token, user) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(TENANT_KEY, user.tenant_id);
    set({ token, user, tenantId: user.tenant_id, error: null });
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TENANT_KEY);
    set({ token: null, user: null, tenantId: null, error: null });
  },

  setError: (msg) => set({ error: msg }),

  /** Restore session from localStorage token on app boot */
  bootstrap: async () => {
    const token = get().token;
    if (!token) return;

    set({ loading: true });
    try {
      const { data } = await authApi.me();
      set({ user: data, loading: false });
    } catch {
      // Token invalid/expired — clear it
      get().logout();
      set({ loading: false });
    }
  },
}));
