import client, { resolveApiV1Base } from './client';

export type ExportType = 'schedule' | 'fabrication' | 'summary';
export type ExportFormat = 'csv' | 'xlsx';
export type ExportStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ExportJobRequest {
  export_type: ExportType;
  format: ExportFormat;
}

export interface ExportJobResponse {
  job_id: string;
  project_id: string;
  tenant_id: string;
  export_type: ExportType;
  format: ExportFormat;
  status: ExportStatus;
  file_path?: string;
  error_log?: string;
  created_at: string;
  updated_at: string;
}

const TOKEN_KEY = 'bd_token';
const TENANT_KEY = 'bd_tenant_id';

export const exportsApi = {
  requestExport: async (projectId: string, request: ExportJobRequest): Promise<ExportJobResponse> => {
    const response = await client.post(`/projects/${projectId}/exports`, request);
    return response.data;
  },

  listExports: async (projectId: string): Promise<ExportJobResponse[]> => {
    const response = await client.get(`/projects/${projectId}/exports`);
    return response.data;
  },

  downloadExport: async (projectId: string, jobId: string, format: ExportFormat): Promise<void> => {
    const token = localStorage.getItem(TOKEN_KEY);
    const tenantId = localStorage.getItem(TENANT_KEY);
    const url = `${resolveApiV1Base()}/projects/${projectId}/exports/${jobId}/download`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(tenantId ? { 'X-Tenant-ID': tenantId } : {}),
      },
    });

    if (!response.ok) {
      throw new Error(`Download failed (${response.status})`);
    }

    const blob = await response.blob();
    const ext = format === 'xlsx' ? 'xlsx' : 'csv';
    const objectUrl = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.style.display = 'none';
    anchor.href = objectUrl;
    anchor.download = `export_${jobId}.${ext}`;
    document.body.appendChild(anchor);
    anchor.click();
    window.URL.revokeObjectURL(objectUrl);
    anchor.remove();
  },
};
