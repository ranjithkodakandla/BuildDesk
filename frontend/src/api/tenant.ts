import client from './client';

export interface TenantProfile {
  tenant_id: string;
  name: string;
  company_name?: string;
  logo_url?: string;
  default_footer?: string;
  standard_notes?: string;
}

export type TenantProfileRequest = Pick<
  TenantProfile,
  'company_name' | 'logo_url' | 'default_footer' | 'standard_notes'
>;

export const tenantApi = {
  getProfile: async (): Promise<TenantProfile> => {
    const res = await client.get('/tenant/profile');
    return res.data;
  },
  updateProfile: async (body: TenantProfileRequest): Promise<TenantProfile> => {
    const res = await client.put('/tenant/profile', body);
    return res.data;
  },
};
