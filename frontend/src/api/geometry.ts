import { apiClient } from './client';

// ── Types ──────────────────────────────────────────────────────────────────

export type ShapeType = 'rectangle' | 'island' | 'vanity' | 'straight_kitchen' | 'l_kitchen';

export interface GeometryRequest {
  shape_type: ShapeType;
  project_id: string;
  tenant_id: string;
  dimensions: Record<string, number | string>;
}

export interface GeometryPiece {
  piece_id: string;
  label: string;
  width: number;
  length: number;
  thickness: number | null;
  area: number;
  notes: string | null;
}

export interface GeometryResponse {
  geometry_id: string;
  template_id: string;
  project_id: string;
  tenant_id: string;
  shape_type: string;
  status: string;
  computed_area: number | null;
  computed_perimeter: number | null;
  dimensions: Record<string, unknown>;
  pieces: GeometryPiece[];
  rectangles: unknown[];
  dimension_lines: unknown[];
  metadata: Record<string, unknown> | null;
  schema_version: string;
}

export interface ExportRequest extends GeometryRequest {}

// ── API functions ──────────────────────────────────────────────────────────

export const geometryApi = {
  create: (body: GeometryRequest) =>
    apiClient.post<GeometryResponse>('/api/v1/geometry', body),

  getById: (geometryId: string) =>
    apiClient.get<GeometryResponse>(`/api/v1/geometry/${geometryId}`),
};

export const exportApi = {
  svg: (body: ExportRequest) =>
    apiClient.post('/api/v1/export/svg', body, { responseType: 'text' }),

  pdf: (body: ExportRequest) =>
    apiClient.post('/api/v1/export/pdf', body, { responseType: 'blob' }),
};

// ── Shape dimension configs ────────────────────────────────────────────────

export interface DimensionField {
  key: string;
  label: string;
  defaultValue: number;
  min?: number;
  max?: number;
  unit?: string;
}

export const SHAPE_DIMENSIONS: Record<ShapeType, DimensionField[]> = {
  rectangle: [
    { key: 'length', label: 'Length', defaultValue: 96, min: 12, max: 240, unit: 'in' },
    { key: 'width', label: 'Width', defaultValue: 42, min: 12, max: 60, unit: 'in' },
  ],
  island: [
    { key: 'length', label: 'Length', defaultValue: 96, min: 24, max: 240, unit: 'in' },
    { key: 'width', label: 'Width', defaultValue: 42, min: 24, max: 60, unit: 'in' },
  ],
  vanity: [
    { key: 'length', label: 'Length', defaultValue: 48, min: 12, max: 120, unit: 'in' },
    { key: 'width', label: 'Width', defaultValue: 22, min: 12, max: 30, unit: 'in' },
  ],
  straight_kitchen: [
    { key: 'length', label: 'Length', defaultValue: 120, min: 36, max: 360, unit: 'in' },
    { key: 'width', label: 'Width', defaultValue: 25, min: 18, max: 42, unit: 'in' },
  ],
  l_kitchen: [
    { key: 'leg1_length', label: 'Leg 1 Length', defaultValue: 120, min: 36, max: 240, unit: 'in' },
    { key: 'leg2_length', label: 'Leg 2 Length', defaultValue: 84, min: 36, max: 240, unit: 'in' },
    { key: 'width', label: 'Width', defaultValue: 25, min: 18, max: 42, unit: 'in' },
  ],
};
