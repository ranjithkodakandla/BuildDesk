import client, { resolveApiV1Base } from './client';
import { ProjectPackage, GeneratePackageRequest } from '../types/packages';

const TOKEN_KEY = 'bd_token';
const TENANT_KEY = 'bd_tenant_id';

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
    return res.data.packages;
  },
  getPdfUrl: (projectId: string, packageId?: string): string => {
    const baseUrl = resolveApiV1Base();
    if (packageId) {
      return `${baseUrl}/projects/${projectId}/packages/${packageId}/pdf`;
    }
    return `${baseUrl}/projects/${projectId}/package/pdf`;
  },
  downloadPdf: async (projectId: string, packageId?: string, version = 'package'): Promise<void> => {
    const token = localStorage.getItem(TOKEN_KEY);
    const tenantId = localStorage.getItem(TENANT_KEY);
    const path = packageId
      ? `/projects/${projectId}/packages/${packageId}/pdf`
      : `/projects/${projectId}/package/pdf`;
    const url = `${resolveApiV1Base()}${path}`;

    const response = await fetch(url, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(tenantId ? { 'X-Tenant-ID': tenantId } : {}),
      },
    });
    if (!response.ok) {
      throw new Error(`PDF download failed (${response.status})`);
    }
    const blob = await response.blob();
    const objectUrl = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = `${version}.pdf`;
    document.body.appendChild(anchor);
    anchor.click();
    window.URL.revokeObjectURL(objectUrl);
    anchor.remove();
  },
};
