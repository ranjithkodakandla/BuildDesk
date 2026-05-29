import client from './client';

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

export const exportsApi = {
  requestExport: async (projectId: string, request: ExportJobRequest): Promise<ExportJobResponse> => {
    const response = await client.post(`/projects/${projectId}/exports`, request);
    return response.data;
  },
  
  listExports: async (projectId: string): Promise<ExportJobResponse[]> => {
    const response = await client.get(`/projects/${projectId}/exports`);
    return response.data;
  },

  downloadExport: (projectId: string, jobId: string) => {
    // In a real implementation we would get a signed URL or fetch as Blob
    // Here we can directly fetch and trigger download using native JS
    const token = localStorage.getItem('token');
    const tenantId = localStorage.getItem('tenant_id') || '11111111-1111-1111-1111-111111111111';
    
    fetch(`${client.defaults.baseURL}/projects/${projectId}/exports/${jobId}/download`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-Tenant-ID': tenantId
      }
    })
    .then(response => {
      if (!response.ok) throw new Error('Download failed');
      return response.blob();
    })
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `export_${jobId}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    })
    .catch(err => console.error(err));
  }
};
