import client from './client';
import { ProjectPackage, GeneratePackageRequest } from '../types/packages';

export const packagesApi = {
  generatePackage: async (projectId: string, req: GeneratePackageRequest): Promise<ProjectPackage> => {
    const res = await client.post(`/projects/${projectId}/package/generate`, req);
    return res.data;
  },
  getPackageStatus: async (projectId: string): Promise<ProjectPackage> => {
    const res = await client.get(`/projects/${projectId}/package/status`);
    return res.data;
  },
  getPdfUrl: (projectId: string): string => {
    const baseUrl = client.defaults.baseURL || 'http://localhost:8000/api/v1';
    return `${baseUrl}/projects/${projectId}/package/pdf`;
  }
};
