import client from './client';
import { Assembly } from '../types/fabrication';

export const assembliesApi = {
  listAssemblies: async (projectId: string): Promise<Assembly[]> => {
    const res = await client.get(`/assemblies`, { params: { project_id: projectId } });
    return res.data;
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
  getSvgPreviewUrl: (assemblyId: string): string => {
    const baseUrl = client.defaults.baseURL || 'http://localhost:8000/api/v1';
    return `${baseUrl}/assemblies/${assemblyId}/preview/svg`;
  }
};
