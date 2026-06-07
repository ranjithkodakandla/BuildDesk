/**
 * Matrix Setup API client  (Phase 6)
 */
import { apiClient } from './client';
import {
  MatrixBulkRequest,
  MatrixBulkResponse,
  MatrixExportResponse,
} from '../types/matrix';

export const matrixApi = {
  /**
   * POST /api/v1/projects/{projectId}/units/bulk-matrix
   * Idempotent bulk unit creation from matrix rows.
   */
  async bulkMatrix(
    projectId: string,
    request: MatrixBulkRequest,
  ): Promise<MatrixBulkResponse> {
    const response = await apiClient.post<MatrixBulkResponse>(
      `/projects/${projectId}/units/bulk-matrix`,
      request,
    );
    return response.data;
  },

  /**
   * GET /api/v1/projects/{projectId}/matrix
   * Export existing project units as matrix rows.
   */
  async getMatrix(projectId: string): Promise<MatrixExportResponse> {
    const response = await apiClient.get<MatrixExportResponse>(
      `/projects/${projectId}/matrix`,
    );
    return response.data;
  },
};
