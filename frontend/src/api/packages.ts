import client, { API_BASE_URL } from './client';
import { ProjectPackage, GeneratePackageRequest } from '../types/packages';

export const packagesApi = {
  generatePackage: async (projectId: string, req: GeneratePackageRequest): Promise<ProjectPackage> => {
    const res = await client.post(`/projects/${projectId}/package/generate`, req);
    return res.data;
  },
  getPackageStatus: async (projectId: string): Promise<ProjectPackage | null> => {
    const packages = await packagesApi.listPackages(projectId);
    if (packages.length === 0) return null;
    return packages[0];
  },
  listPackages: async (projectId: string): Promise<ProjectPackage[]> => {
    const res = await client.get(`/projects/${projectId}/packages`);
    return res.data.packages ?? [];
  },
  getPdfUrl: (projectId: string, packageId?: string): string => {
    const baseUrl = client.defaults.baseURL || API_BASE_URL;
    if (packageId) {
      return `${baseUrl}/projects/${projectId}/packages/${packageId}/pdf`;
    }
    return `${baseUrl}/projects/${projectId}/package/pdf`;
  }
};
