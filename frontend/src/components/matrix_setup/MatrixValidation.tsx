/**
 * MatrixValidation  (Phase 6)
 * Pure validation logic for matrix grid rows — no React state.
 */
import { GridRow } from '../../types/matrix';

export interface RowValidationError {
  field:   keyof GridRow | 'general';
  message: string;
}

export interface RowValidationResult {
  valid:  boolean;
  errors: RowValidationError[];
}

const VALID_TEMPLATE_IDS = new Set([
  'KITCHEN_STRAIGHT',
  'KITCHEN_STRAIGHT_REF',
  'KITCHEN_L',
  'PLAIN_ISLAND',
  'SINGLE_VANITY',
  'OFFSET_VANITY',
  'DOUBLE_VANITY',
  'COMPACT_VANITY',
]);

export function validateRow(row: GridRow): RowValidationResult {
  const errors: RowValidationError[] = [];

  if (!row.building.trim()) {
    errors.push({ field: 'building', message: 'Building is required' });
  } else if (row.building.length > 20) {
    errors.push({ field: 'building', message: 'Max 20 characters' });
  }

  if (!row.floor.trim()) {
    errors.push({ field: 'floor', message: 'Floor is required' });
  } else if (row.floor.length > 20) {
    errors.push({ field: 'floor', message: 'Max 20 characters' });
  }

  if (!row.flat.trim()) {
    errors.push({ field: 'flat', message: 'Flat/Unit is required' });
  } else if (row.flat.length > 50) {
    errors.push({ field: 'flat', message: 'Max 50 characters' });
  }

  if (!row.template.trim()) {
    errors.push({ field: 'template', message: 'Template is required' });
  } else if (!VALID_TEMPLATE_IDS.has(row.template)) {
    errors.push({ field: 'template', message: `Unknown template "${row.template}"` });
  }

  return { valid: errors.length === 0, errors };
}

export function validateRows(rows: GridRow[]): Map<string, RowValidationResult> {
  const map = new Map<string, RowValidationResult>();
  for (const row of rows) {
    map.set(row._id, validateRow(row));
  }
  return map;
}

export function firstErrorForField(
  result: RowValidationResult | undefined,
  field: keyof GridRow,
): string | null {
  if (!result) return null;
  const err = result.errors.find(e => e.field === field);
  return err?.message ?? null;
}
