/**
 * Matrix Setup types  (Phase 6)
 * Matches backend api/matrix_schemas.py
 */

// ---------------------------------------------------------------------------
// Row model — used both for input grid state and for the API request
// ---------------------------------------------------------------------------

export interface MatrixRow {
  building:  string;
  floor:     string;
  flat:      string;
  template:  string;
  mirror:    boolean;
  ada:       boolean;
}

// ---------------------------------------------------------------------------
// API request / response
// ---------------------------------------------------------------------------

export interface MatrixBulkRequest {
  rows: MatrixRow[];
}

export type RowStatus = 'created' | 'existing' | 'error';

export interface MatrixRowResult {
  row_index:    number;
  building:     string;
  floor:        string;
  flat:         string;
  template:     string;
  mirror:       boolean;
  ada:          boolean;
  status:       RowStatus;
  unit_id:      string | null;
  unit_type_id: string | null;
  building_id:  string | null;
  floor_id:     string | null;
  error:        string | null;
}

export interface MatrixBulkResponse {
  rows_processed:   number;
  units_created:    number;
  units_existing:   number;
  units_errored:    number;
  buildings_total:  number;
  floors_total:     number;
  unit_types_total: number;
  results:          MatrixRowResult[];
}

export interface MatrixExportRow extends MatrixRow {
  unit_id:      string | null;
  building_id:  string | null;
  floor_id:     string | null;
  unit_type_id: string | null;
}

export interface MatrixExportResponse {
  rows:  MatrixExportRow[];
  total: number;
}

// ---------------------------------------------------------------------------
// UI-only: editable grid row (adds local state)
// ---------------------------------------------------------------------------

export type RowEditState = 'idle' | 'editing' | 'saved' | 'error';

export interface GridRow extends MatrixRow {
  /** Local unique key for React list rendering */
  _id: string;
  /** Post-submit status from the API */
  _status?: RowStatus;
  /** Error message if status === 'error' */
  _error?: string;
  /** Unit ID returned after successful submit */
  _unit_id?: string;
}
