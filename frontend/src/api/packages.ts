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
  listPackages: async (projectId: string): Promise<ProjectPackage[]> => {
    const res = await client.get(`/projects/${projectId}/packages`);
    return res.data.packages; // assuming response is { packages: [...] }
  },
  getPdfUrl: (projectId: string, packageId?: string): string => {
    const baseUrl = client.defaults.baseURL || 'http://localhost:8000/api/v1';
    if (packageId) {
      return `${baseUrl}/projects/${projectId}/packages/${packageId}/pdf`;
    }
    return `${baseUrl}/projects/${projectId}/package/pdf`;
  }
};
