import { api } from './client';

export interface ImportRecordError {
  row_index: number;
  column?: string;
  message: string;
  severity: string;
}

export interface ImportMapping {
  unit_number_col?: string;
  unit_type_col?: string;
  building_col?: string;
  floor_col?: string;
}

export interface ImportJobResponse {
  job_id: string;
  project_id: string;
  tenant_id: string;
  filename: string;
  status: string;
  total_rows: number;
  processed_rows: number;
  error_log: ImportRecordError[];
  column_mapping?: ImportMapping;
  created_at: string;
  updated_at: string;
}

export interface ImportValidationPreviewResponse {
  is_valid: boolean;
  total_rows: number;
  valid_rows: number;
  errors: ImportRecordError[];
}

export interface ImportExecutionResponse {
  status: string;
  units_created: number;
  assemblies_created: number;
}

export const importsApi = {
  uploadFile: async (projectId: string, file: File): Promise<ImportJobResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post(`/projects/${projectId}/imports`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  updateMapping: async (projectId: string, jobId: string, mapping: ImportMapping): Promise<ImportJobResponse> => {
    const { data } = await api.put(`/projects/${projectId}/imports/${jobId}/mapping`, { mapping });
    return data;
  },

  validateImport: async (projectId: string, jobId: string, file: File): Promise<ImportValidationPreviewResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post(`/projects/${projectId}/imports/${jobId}/validate`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  executeImport: async (projectId: string, jobId: string, file: File): Promise<ImportExecutionResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post(`/projects/${projectId}/imports/${jobId}/execute`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },
};
