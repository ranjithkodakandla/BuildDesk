/**
 * MatrixGrid  (Phase 6)
 * Spreadsheet-style editable grid for bulk unit setup.
 *
 * Features:
 *  - Inline cell editing (click to edit any cell)
 *  - Copy/paste from Excel (tab-delimited rows in clipboard)
 *  - Row validation inline
 *  - Mirror / ADA toggle checkboxes
 *  - Template dropdown backed by the template registry
 *  - Visual status indicator after submit (created / existing / error)
 */
import React, { useCallback, useRef } from 'react';
import { GridRow } from '../../types/matrix';
import { RowValidationResult, firstErrorForField } from './MatrixValidation';
import { parseTextToRows } from './MatrixImportExport';

// ---------------------------------------------------------------------------
// Template options (must stay in sync with backend registry)
// ---------------------------------------------------------------------------

export const TEMPLATE_OPTIONS: { id: string; label: string; category: string }[] = [
  { id: 'KITCHEN_STRAIGHT',     label: 'Kitchen Straight',       category: 'kitchen' },
  { id: 'KITCHEN_STRAIGHT_REF', label: 'Kitchen + REF',          category: 'kitchen' },
  { id: 'KITCHEN_L',            label: 'L-Kitchen',              category: 'kitchen' },
  { id: 'PLAIN_ISLAND',         label: 'Plain Island',           category: 'island'  },
  { id: 'SINGLE_VANITY',        label: 'Single Vanity',          category: 'vanity'  },
  { id: 'OFFSET_VANITY',        label: 'Offset Vanity',          category: 'vanity'  },
  { id: 'DOUBLE_VANITY',        label: 'Double Vanity',          category: 'vanity'  },
  { id: 'COMPACT_VANITY',       label: 'Compact Vanity',         category: 'vanity'  },
];

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status?: string }) {
  if (!status) return null;
  const cfg: Record<string, { cls: string; label: string }> = {
    created:  { cls: 'bg-green-100 text-green-700',  label: 'Created'  },
    existing: { cls: 'bg-slate-100 text-slate-600',  label: 'Existing' },
    error:    { cls: 'bg-red-100 text-red-700',      label: 'Error'    },
  };
  const c = cfg[status] ?? { cls: 'bg-gray-100 text-gray-500', label: status };
  return (
    <span className={`inline-block px-1.5 py-0.5 text-xs font-semibold rounded ${c.cls}`}>
      {c.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Inline text cell
// ---------------------------------------------------------------------------

interface TextCellProps {
  value:       string;
  placeholder: string;
  hasError:    boolean;
  onChange:    (v: string) => void;
  onKeyDown?:  (e: React.KeyboardEvent<HTMLInputElement>) => void;
  inputRef?:   React.Ref<HTMLInputElement>;
  className?:  string;
}

function TextCell({
  value, placeholder, hasError, onChange, onKeyDown, inputRef, className = '',
}: TextCellProps) {
  return (
    <input
      ref={inputRef}
      value={value}
      placeholder={placeholder}
      onChange={e => onChange(e.target.value)}
      onKeyDown={onKeyDown}
      className={`
        w-full px-1.5 py-1 text-sm bg-transparent border-0 outline-none
        focus:ring-1 focus:ring-inset rounded
        ${hasError ? 'ring-1 ring-red-400 bg-red-50' : 'focus:ring-[#3b82f6]'}
        ${className}
      `}
      spellCheck={false}
    />
  );
}

// ---------------------------------------------------------------------------
// Main MatrixGrid
// ---------------------------------------------------------------------------

interface Props {
  rows:           GridRow[];
  validation:     Map<string, RowValidationResult>;
  selectedIds:    Set<string>;
  onRowChange:    (id: string, patch: Partial<GridRow>) => void;
  onRowDelete:    (id: string) => void;
  onPasteRows:    (rows: GridRow[]) => void;
  onSelectRow:    (id: string, checked: boolean) => void;
  onSelectAll:    (checked: boolean) => void;
  onLaunchBuilder?: (row: GridRow) => void;
}

export const MatrixGrid: React.FC<Props> = ({
  rows, validation, selectedIds, onRowChange, onRowDelete,
  onPasteRows, onSelectRow, onSelectAll, onLaunchBuilder,
}) => {
  const allSelected = rows.length > 0 && rows.every(r => selectedIds.has(r._id));
  const someSelected = !allSelected && rows.some(r => selectedIds.has(r._id));
  const tableRef = useRef<HTMLDivElement>(null);

  // ── Paste handler: supports Excel copy (tab-separated rows) ─────────────
  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const text = e.clipboardData.getData('text/plain');
    if (!text) return;
    // Only intercept if it looks like multi-column data (has tabs or newlines)
    if (text.includes('\t') || text.includes('\n')) {
      e.preventDefault();
      const result = parseTextToRows(text);
      if (result.rows.length > 0) onPasteRows(result.rows);
    }
  }, [onPasteRows]);

  if (rows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center px-6">
        <div className="text-5xl mb-4 opacity-50">📐</div>
        <p className="text-base font-bold text-gray-700 mb-1">No units configured yet</p>
        <p className="text-sm text-gray-500 mb-4 max-w-xs">
          Add rows below, use Quick Fill to generate a floor plan, or paste directly from Excel.
        </p>
        <div className="flex flex-wrap justify-center gap-3 text-xs text-gray-400">
          <span className="px-3 py-1.5 bg-gray-100 rounded-full">➕ Add Row button above</span>
          <span className="px-3 py-1.5 bg-gray-100 rounded-full">⚡ Quick Fill for bulk entry</span>
          <span className="px-3 py-1.5 bg-gray-100 rounded-full">⌘V / Ctrl+V paste from Excel</span>
        </div>
      </div>
    );
  }

  return (
    <div ref={tableRef} onPaste={handlePaste} className="overflow-x-auto">
      <table className="min-w-full text-sm border-separate border-spacing-0">
        {/* ── Header ─────────────────────────────────────────────────── */}
        <thead>
          <tr className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
            {/* Select-all checkbox */}
            <th className="w-8 px-2 py-2 text-center bg-gray-50 border-b border-gray-200">
              <input
                type="checkbox"
                checked={allSelected}
                ref={el => { if (el) el.indeterminate = someSelected; }}
                onChange={e => onSelectAll(e.target.checked)}
                className="w-3.5 h-3.5 rounded border-[#cbd5e1] text-[#1e293b] cursor-pointer"
              />
            </th>
            <th className="w-6 px-2 py-2 text-center text-gray-300 font-normal">#</th>
            <th className="px-2 py-2 text-left bg-gray-50 border-b border-gray-200 rounded-tl">Building</th>
            <th className="px-2 py-2 text-left bg-gray-50 border-b border-gray-200">Floor</th>
            <th className="px-2 py-2 text-left bg-gray-50 border-b border-gray-200">Flat / Unit</th>
            <th className="px-2 py-2 text-left bg-gray-50 border-b border-gray-200 min-w-[160px]">Template</th>
            <th className="px-2 py-2 text-center bg-gray-50 border-b border-gray-200 w-16">Mirror</th>
            <th className="px-2 py-2 text-center bg-gray-50 border-b border-gray-200 w-16">ADA</th>
            <th className="px-2 py-2 text-center bg-gray-50 border-b border-gray-200 w-20">Status</th>
            <th className="px-2 py-2 bg-gray-50 border-b border-gray-200 rounded-tr w-16"></th>
          </tr>
        </thead>

        {/* ── Body ───────────────────────────────────────────────────── */}
        <tbody>
          {rows.map((row, idx) => {
            const vr = validation.get(row._id);
            const hasAnyError = vr && !vr.valid;

            return (
              <tr
                key={row._id}
                className={`
                  group border-b border-[#f1f5f9] hover:bg-[#f8fafc] transition-colors
                  ${selectedIds.has(row._id) ? 'bg-[#eff6ff]' : ''}
                  ${row._status === 'error' ? 'bg-red-50/30' : ''}
                  ${row._status === 'created' ? 'bg-green-50/20' : ''}
                `}
                style={{ minHeight: '44px' }}
              >
                {/* Row select checkbox */}
                <td className="px-2 py-1.5 text-center">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(row._id)}
                    onChange={e => onSelectRow(row._id, e.target.checked)}
                    className="w-3.5 h-3.5 rounded border-[#cbd5e1] text-[#1e293b] cursor-pointer"
                  />
                </td>
                {/* Row number */}
                <td className="px-2 py-1.5 text-center text-xs text-gray-300 select-none">
                  {idx + 1}
                </td>

                {/* Building */}
                <td className="px-1 py-1">
                  <TextCell
                    value={row.building}
                    placeholder="A"
                    hasError={!!firstErrorForField(vr, 'building')}
                    onChange={v => onRowChange(row._id, { building: v })}
                  />
                  {firstErrorForField(vr, 'building') && (
                    <p className="text-xs text-red-500 px-1.5">{firstErrorForField(vr, 'building')}</p>
                  )}
                </td>

                {/* Floor */}
                <td className="px-1 py-1">
                  <TextCell
                    value={row.floor}
                    placeholder="1"
                    hasError={!!firstErrorForField(vr, 'floor')}
                    onChange={v => onRowChange(row._id, { floor: v })}
                  />
                  {firstErrorForField(vr, 'floor') && (
                    <p className="text-xs text-red-500 px-1.5">{firstErrorForField(vr, 'floor')}</p>
                  )}
                </td>

                {/* Flat */}
                <td className="px-1 py-1">
                  <TextCell
                    value={row.flat}
                    placeholder="101"
                    hasError={!!firstErrorForField(vr, 'flat')}
                    onChange={v => onRowChange(row._id, { flat: v })}
                  />
                  {firstErrorForField(vr, 'flat') && (
                    <p className="text-xs text-red-500 px-1.5">{firstErrorForField(vr, 'flat')}</p>
                  )}
                </td>

                {/* Template dropdown */}
                <td className="px-1 py-1">
                  <select
                    value={row.template}
                    onChange={e => onRowChange(row._id, { template: e.target.value })}
                    className={`
                      w-full px-1.5 py-1 text-sm bg-white border rounded cursor-pointer
                      focus:outline-none focus:ring-1 focus:ring-[#3b82f6]
                      ${firstErrorForField(vr, 'template') ? 'border-red-400 bg-red-50' : 'border-gray-200'}
                    `}
                  >
                    <option value="">Select template…</option>
                    <optgroup label="Kitchen">
                      {TEMPLATE_OPTIONS.filter(t => t.category === 'kitchen').map(t => (
                        <option key={t.id} value={t.id}>{t.label}</option>
                      ))}
                    </optgroup>
                    <optgroup label="Vanity">
                      {TEMPLATE_OPTIONS.filter(t => t.category === 'vanity').map(t => (
                        <option key={t.id} value={t.id}>{t.label}</option>
                      ))}
                    </optgroup>
                    <optgroup label="Island">
                      {TEMPLATE_OPTIONS.filter(t => t.category === 'island').map(t => (
                        <option key={t.id} value={t.id}>{t.label}</option>
                      ))}
                    </optgroup>
                  </select>
                </td>

                {/* Mirror toggle */}
                <td className="px-1 py-1 text-center">
                  <input
                    type="checkbox"
                    checked={row.mirror}
                    onChange={e => onRowChange(row._id, { mirror: e.target.checked })}
                    className="w-4 h-4 rounded border-[#cbd5e1] text-[#1e293b] cursor-pointer"
                    title="Mirror (flip left ↔ right)"
                  />
                </td>

                {/* ADA toggle */}
                <td className="px-1 py-1 text-center">
                  <input
                    type="checkbox"
                    checked={row.ada}
                    onChange={e => onRowChange(row._id, { ada: e.target.checked })}
                    className="w-4 h-4 rounded border-[#cbd5e1] text-[#1e293b] cursor-pointer"
                    title="ADA accessible variant"
                  />
                </td>

                {/* Status */}
                <td className="px-1 py-1 text-center">
                  {row._status ? (
                    <StatusBadge status={row._status} />
                  ) : hasAnyError ? (
                    <span className="text-xs text-red-400" title={vr?.errors.map(e => e.message).join('; ')}>
                      ⚠
                    </span>
                  ) : null}
                  {row._error && (
                    <p className="text-xs text-red-500 mt-0.5" title={row._error}>
                      {row._error.slice(0, 30)}…
                    </p>
                  )}
                </td>

                {/* Actions */}
                <td className="px-1 py-1 text-right">
                  <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {onLaunchBuilder && row._unit_id && (
                      <button
                        type="button"
                        onClick={() => onLaunchBuilder(row)}
                        title="Open in Basic Builder"
                        className="text-[#64748b] hover:text-[#1e293b] text-xs px-1.5 py-0.5 rounded hover:bg-[#f1f5f9] transition"
                      >
                        ⚡
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => onRowDelete(row._id)}
                      title="Delete row"
                      className="text-red-400 hover:text-red-600 text-xs px-1.5 py-0.5 rounded hover:bg-red-50 transition"
                    >
                      ×
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
