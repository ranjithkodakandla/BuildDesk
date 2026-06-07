/**
 * MatrixImportExport  (Phase 6 / P1 enhanced Phase 7.1)
 * CSV import and export for the matrix grid.
 *
 * CSV format (header row):
 *   Building,Floor,Flat,Template,Mirror,ADA
 *
 * Excel paste format (tab-separated without header).
 * Phase 7.1: parseTextToRows now returns {rows, errors} with per-row/column detail.
 */
import React, { useRef } from 'react';
import { GridRow } from '../../types/matrix';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeId(): string {
  return Math.random().toString(36).slice(2, 10);
}

// Valid template IDs (must stay in sync with backend registry)
const VALID_TEMPLATE_IDS = new Set([
  'KITCHEN_STRAIGHT', 'KITCHEN_STRAIGHT_REF', 'KITCHEN_L', 'PLAIN_ISLAND',
  'SINGLE_VANITY', 'OFFSET_VANITY', 'DOUBLE_VANITY', 'COMPACT_VANITY',
]);

export interface ImportError {
  sourceRow: number;   // 1-based row in source file (after header skip)
  column:    string;
  value:     string;
  message:   string;
}

export interface ParseResult {
  rows:   GridRow[];
  errors: ImportError[];
}

function rowFromValues(
  building: string,
  floor:    string,
  flat:     string,
  template: string,
  mirror:   string | boolean,
  ada:      string | boolean,
): GridRow {
  return {
    _id:      makeId(),
    building: building.trim(),
    floor:    floor.trim(),
    flat:     flat.trim(),
    template: template.trim().toUpperCase(),
    mirror:   typeof mirror === 'boolean' ? mirror : mirror.toLowerCase() === 'true' || mirror === '1',
    ada:      typeof ada    === 'boolean' ? ada    : ada.toLowerCase()    === 'true' || ada    === '1',
  };
}

function parseBoolField(val: string): boolean | null {
  const v = val.toLowerCase().trim();
  if (['true', '1', 'yes', 'y'].includes(v)) return true;
  if (['false', '0', 'no', 'n', ''].includes(v)) return false;
  return null;
}

/** Parse a CSV or TSV blob into GridRows + per-row/column errors (Phase 7.1). */
export function parseTextToRows(text: string): ParseResult {
  const lines = text.split(/\r?\n/).filter(l => l.trim());
  if (!lines.length) return { rows: [], errors: [] };

  const sep = lines[0].includes('\t') ? '\t' : ',';
  const rows: GridRow[]   = [];
  const errors: ImportError[] = [];
  let startIdx = 0;

  const firstCell = lines[0].split(sep)[0].trim().toLowerCase();
  if (['building', 'bldg', 'blg', '#'].includes(firstCell)) startIdx = 1;

  for (let i = startIdx; i < lines.length; i++) {
    const srcRow = i - startIdx + 1;
    const parts  = lines[i].split(sep).map(p => p.trim().replace(/^"|"$/g, ''));
    const [
      building = '',
      floor    = '',
      flat     = '',
      template = '',
      mirrorRaw = 'false',
      adaRaw    = 'false',
    ] = parts;

    let rowHasError = false;

    if (!building) {
      errors.push({ sourceRow: srcRow, column: 'Building', value: building, message: 'Building is required' });
      rowHasError = true;
    }
    if (!floor) {
      errors.push({ sourceRow: srcRow, column: 'Floor', value: floor, message: 'Floor is required' });
      rowHasError = true;
    }
    if (!flat) {
      errors.push({ sourceRow: srcRow, column: 'Flat', value: flat, message: 'Flat/Unit code is required' });
      rowHasError = true;
    }
    const tmplUpper = template.trim().toUpperCase();
    if (!tmplUpper) {
      errors.push({ sourceRow: srcRow, column: 'Template', value: template, message: 'Template is required' });
      rowHasError = true;
    } else if (!VALID_TEMPLATE_IDS.has(tmplUpper)) {
      errors.push({
        sourceRow: srcRow,
        column:    'Template',
        value:     template,
        message:   `"${template}" is not a valid template ID. Expected one of: ${Array.from(VALID_TEMPLATE_IDS).join(', ')}`,
      });
      rowHasError = true;
    }
    if (parseBoolField(mirrorRaw) === null) {
      errors.push({ sourceRow: srcRow, column: 'Mirror', value: mirrorRaw, message: 'Expected true/false/1/0' });
      rowHasError = true;
    }
    if (parseBoolField(adaRaw) === null) {
      errors.push({ sourceRow: srcRow, column: 'ADA', value: adaRaw, message: 'Expected true/false/1/0' });
      rowHasError = true;
    }

    if (!rowHasError) {
      rows.push(rowFromValues(building, floor, flat, template, mirrorRaw, adaRaw));
    }
  }
  return { rows, errors };
}

/** Convert grid rows to CSV text. */
export function rowsToCsv(rows: GridRow[]): string {
  const header = 'Building,Floor,Flat,Template,Mirror,ADA';
  const body = rows.map(r =>
    [r.building, r.floor, r.flat, r.template, r.mirror, r.ada]
      .map(v => String(v).includes(',') ? `"${v}"` : v)
      .join(',')
  ).join('\n');
  return `${header}\n${body}`;
}

/** Download a text file in the browser. */
function downloadText(content: string, filename: string, mimeType = 'text/csv') {
  const blob = new Blob([content], { type: mimeType });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  rows:      GridRow[];
  projectId: string;
  onImport:  (result: ParseResult) => void;
}

export const MatrixImportExport: React.FC<Props> = ({ rows, projectId, onImport }) => {
  const fileRef = useRef<HTMLInputElement>(null);

  function handleExport() {
    const csv = rowsToCsv(rows);
    downloadText(csv, `matrix-${projectId}.csv`);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      const result = parseTextToRows(text);
      onImport(result);
    };
    reader.readAsText(file);
    e.target.value = '';
  }

  return (
    <div className="flex items-center gap-2">
      <input
        ref={fileRef}
        type="file"
        accept=".csv,.tsv,.txt"
        className="hidden"
        onChange={handleFileChange}
      />

      <button
        type="button"
        onClick={() => fileRef.current?.click()}
        title="Import rows from CSV or Excel export"
        aria-label="Import CSV file"
        className="flex items-center gap-1.5 px-3 py-2 min-h-[40px] text-xs font-medium text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 transition"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
        Import CSV
      </button>

      <button
        type="button"
        onClick={handleExport}
        disabled={rows.length === 0}
        title="Export rows to CSV (opens in Excel)"
        aria-label="Export to CSV"
        className="flex items-center gap-1.5 px-3 py-2 min-h-[40px] text-xs font-medium text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 transition disabled:opacity-40"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Export CSV
      </button>
    </div>
  );
};
