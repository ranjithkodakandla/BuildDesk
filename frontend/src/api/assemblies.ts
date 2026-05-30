import client, { API_BASE_URL } from './client';
import { Assembly } from '../types/fabrication';

export const assembliesApi = {
  listAssemblies: async (projectId: string): Promise<Assembly[]> => {
    const res = await client.get(`/assemblies`, { params: { project_id: projectId } });
    const data = res.data;
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.assemblies)) return data.assemblies;
    return [];
  },
  getAssembly: async (assemblyId: string): Promise<Assembly> => {
    const res = await client.get(`/assemblies/${assemblyId}`);
    return res.data;
  },
  createAssembly: async (assembly: Omit<Assembly, 'assembly_id'>): Promise<Assembly> => {
    const res = await client.post(`/assemblies`, assembly);
    return res.data;
  },
  updateAssembly: async (assemblyId: string, assembly: Omit<Assembly, 'assembly_id'>): Promise<Assembly> => {
    const res = await client.put(`/assemblies/${assemblyId}`, assembly);
    return res.data;
  },
  deleteAssembly: async (assemblyId: string): Promise<void> => {
    await client.delete(`/assemblies/${assemblyId}`);
  },
  duplicateAssembly: async (assemblyId: string, data: any): Promise<Assembly> => {
    const res = await client.post(`/assemblies/${assemblyId}/duplicate`, data);
    return res.data;
  },
  getSvgPreviewUrl: (assemblyId: string): string => {
    const baseUrl = client.defaults.baseURL || API_BASE_URL;
    return `${baseUrl}/assemblies/${assemblyId}/preview/svg`;
  }
};
