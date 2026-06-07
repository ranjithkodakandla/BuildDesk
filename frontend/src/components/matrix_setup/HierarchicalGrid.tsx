/**
 * HierarchicalGrid  (Phase 8.5 → Phase 2 UX polish)
 * Cross-tab Building × Floor grid for project setup.
 *
 * Each cell = one Building+Floor intersection.
 * Unit codes are comma-separated within each cell.
 * Selection (click cell/header) drives the AssignmentPanel.
 *
 * Phase 2 changes:
 *  - CellInput sub-component: Enter → commit+blur, Escape → restore+blur
 *  - Tighter cell min-width (120px vs 140px)
 *  - Syncs from parent only when not focused (safe for bulk ops)
 */
import React, { useMemo, useCallback, useState, useRef, useEffect } from 'react';
import { GridRow } from '../../types/matrix';
import { RowValidationResult } from './MatrixValidation';
import { TEMPLATE_OPTIONS } from './MatrixGrid';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function cellKey(building: string, floor: string): string {
  return `${building}::${floor}`;
}

function smartSort(a: string, b: string): number {
  const na = parseFloat(a), nb = parseFloat(b);
  if (!isNaN(na) && !isNaN(nb)) return na - nb;
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
}

function shortTemplateLabel(id: string): string {
  const t = TEMPLATE_OPTIONS.find(o => o.id === id);
  if (!t) return id;
  return t.label
    .replace('Kitchen', 'Kitch.')
    .replace('Vanity', 'Van.')
    .replace('Island', 'Isl.')
    .replace('Straight', 'Str.')
    .replace('Compact', 'Cmpct.');
}

// ---------------------------------------------------------------------------
// CellInput — controlled input with Enter/Escape keyboard handling
// Matches StoneDesk: Enter = commit+blur, Escape = restore+blur
// ---------------------------------------------------------------------------

interface CellInputProps {
  initialValue: string;
  building:     string;
  floor:        string;
  isSelected:   boolean;
  hasErrors:    boolean;
  onCommit:     (building: string, floor: string, value: string) => void;
}

function CellInput({ initialValue, building, floor, isSelected, hasErrors, onCommit }: CellInputProps) {
  const [draft, setDraft]     = useState(initialValue);
  const savedRef              = useRef(initialValue);   // value at focus start (for Escape)
  const cancelRef             = useRef(false);          // skip onBlur commit when Escaping
  const focusedRef            = useRef(false);          // suppress external sync while typing

  // Sync from parent only when not focused — safe for bulk assignment / load
  useEffect(() => {
    if (!focusedRef.current) setDraft(initialValue);
  }, [initialValue]);

  return (
    <input
      type="text"
      value={draft}
      placeholder={`${floor}01, ${floor}02`}
      onChange={e => setDraft(e.target.value)}
      onFocus={() => {
        focusedRef.current = true;
        cancelRef.current  = false;
        savedRef.current   = draft;          // capture pre-edit value
      }}
      onBlur={() => {
        focusedRef.current = false;
        if (!cancelRef.current) onCommit(building, floor, draft);
        cancelRef.current = false;
      }}
      onKeyDown={e => {
        if (e.key === 'Enter') {
          e.preventDefault();
          onCommit(building, floor, draft);
          (e.target as HTMLInputElement).blur();
        } else if (e.key === 'Escape') {
          e.preventDefault();
          cancelRef.current = true;
          setDraft(savedRef.current);        // restore to pre-edit value
          (e.target as HTMLInputElement).blur();
        }
      }}
      onClick={e => e.stopPropagation()}
      className={`
        grid-cell
        ${isSelected ? 'border-[#3b82f6]' : ''}
        ${hasErrors  ? 'border-red-300'   : ''}
      `}
      spellCheck={false}
    />
  );
}

// ---------------------------------------------------------------------------
// Per-cell derived state
// ---------------------------------------------------------------------------

interface CellData {
  units:          string;   // comma-separated unit codes
  template:       string;
  mirror:         boolean;
  ada:            boolean;
  rowCount:       number;
  errorCount:     number;
  createdCount:   number;
  existingCount:  number;
}

function buildCellMap(
  rows:       GridRow[],
  validation: Map<string, RowValidationResult>,
): Map<string, CellData> {
  const map = new Map<string, CellData>();
  for (const row of rows) {
    if (!row.building || !row.floor) continue;
    const key = cellKey(row.building, row.floor);
    if (!map.has(key)) {
      map.set(key, {
        units: '', template: row.template, mirror: row.mirror, ada: row.ada,
        rowCount: 0, errorCount: 0, createdCount: 0, existingCount: 0,
      });
    }
    const cell = map.get(key)!;
    if (row.flat) {
      const existing = cell.units ? cell.units.split(',').map(s => s.trim()) : [];
      if (!existing.includes(row.flat.trim())) {
        cell.units = existing.length ? `${cell.units}, ${row.flat.trim()}` : row.flat.trim();
      }
    }
    cell.template = row.template || cell.template;
    cell.mirror   = row.mirror;
    cell.ada      = row.ada;
    cell.rowCount++;
    const vr = validation.get(row._id);
    if (vr && !vr.valid) cell.errorCount++;
    if (row._status === 'created')  cell.createdCount++;
    if (row._status === 'existing') cell.existingCount++;
  }
  return map;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  rows:              GridRow[];
  validation:        Map<string, RowValidationResult>;
  selectedCells:     Set<string>;
  onSelectionChange: (newSelection: Set<string>) => void;
  onCellUnits:       (building: string, floor: string, units: string) => void;
}

export const HierarchicalGrid: React.FC<Props> = ({
  rows,
  validation,
  selectedCells,
  onSelectionChange,
  onCellUnits,
}) => {
  const buildings = useMemo(() => {
    const s = new Set(rows.map(r => r.building).filter(Boolean));
    return Array.from(s).sort(smartSort);
  }, [rows]);

  const floors = useMemo(() => {
    const s = new Set(rows.map(r => r.floor).filter(Boolean));
    return Array.from(s).sort(smartSort);
  }, [rows]);

  const cellMap = useMemo(
    () => buildCellMap(rows, validation),
    [rows, validation],
  );

  const allKeys = useMemo(
    () => buildings.flatMap(b => floors.map(f => cellKey(b, f))),
    [buildings, floors],
  );
  const allSelected = allKeys.length > 0 && allKeys.every(k => selectedCells.has(k));

  // ── Selection handlers ───────────────────────────────────────────────────

  const toggleCell = useCallback((key: string) => {
    const next = new Set(selectedCells);
    next.has(key) ? next.delete(key) : next.add(key);
    onSelectionChange(next);
  }, [selectedCells, onSelectionChange]);

  const toggleColumn = useCallback((building: string) => {
    const colKeys = floors.map(f => cellKey(building, f));
    const allColSelected = colKeys.every(k => selectedCells.has(k));
    const next = new Set(selectedCells);
    if (allColSelected) colKeys.forEach(k => next.delete(k));
    else colKeys.forEach(k => next.add(k));
    onSelectionChange(next);
  }, [floors, selectedCells, onSelectionChange]);

  const toggleRow = useCallback((floor: string) => {
    const rowKeys = buildings.map(b => cellKey(b, floor));
    const allRowSelected = rowKeys.every(k => selectedCells.has(k));
    const next = new Set(selectedCells);
    if (allRowSelected) rowKeys.forEach(k => next.delete(k));
    else rowKeys.forEach(k => next.add(k));
    onSelectionChange(next);
  }, [buildings, selectedCells, onSelectionChange]);

  const toggleAll = useCallback(() => {
    if (allSelected) onSelectionChange(new Set());
    else onSelectionChange(new Set(allKeys));
  }, [allSelected, allKeys, onSelectionChange]);

  // ── Empty state ──────────────────────────────────────────────────────────

  if (buildings.length === 0 || floors.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center px-6">
        <p className="text-xs font-medium text-[#334155] mb-1">No units configured yet</p>
        <p className="text-xs text-[#94a3b8] max-w-xs">
          Enter buildings &amp; floors above and click Generate, or import CSV, or paste from Excel (⌘V).
        </p>
      </div>
    );
  }

  // ── Grid ─────────────────────────────────────────────────────────────────

  return (
    <div className="overflow-x-auto">
      <table
        className="text-xs border-separate border-spacing-0 w-full"
        style={{ minWidth: `${70 + buildings.length * 130}px` }}
      >
        {/* ── Column headers (buildings) ──────────────────────────────── */}
        <thead>
          <tr>
            {/* Corner: select all */}
            <th className="sticky left-0 z-10 px-2 py-1.5 bg-[#f1f5f9] border-b border-r border-[#e2e8f0] min-w-[70px]">
              <button
                onClick={toggleAll}
                className="flex items-center gap-1 text-[#64748b] hover:text-[#1e293b] transition"
                title={allSelected ? 'Deselect all' : 'Select all'}
              >
                <span className={`w-3 h-3 border rounded flex items-center justify-center text-[8px] font-bold
                  ${allSelected ? 'bg-[#1e293b] border-[#1e293b] text-white' : 'border-[#94a3b8]'}`}>
                  {allSelected ? '✓' : ''}
                </span>
                <span className="font-medium">Floor</span>
              </button>
            </th>
            {buildings.map(b => {
              const colKeys    = floors.map(f => cellKey(b, f));
              const colSelected = colKeys.every(k => selectedCells.has(k));
              return (
                <th
                  key={b}
                  onClick={() => toggleColumn(b)}
                  title={`Select all in Building ${b}`}
                  className={`
                    px-2 py-1.5 border-b border-r border-[#e2e8f0] font-bold uppercase tracking-wider
                    cursor-pointer select-none transition
                    ${colSelected
                      ? 'bg-[#1e293b] text-white'
                      : 'bg-[#f1f5f9] text-[#334155] hover:bg-[#e2e8f0]'
                    }
                  `}
                >
                  Bldg {b}
                </th>
              );
            })}
          </tr>
        </thead>

        {/* ── Rows (floors) ───────────────────────────────────────────── */}
        <tbody>
          {floors.map(floor => {
            const rowKeys    = buildings.map(b => cellKey(b, floor));
            const rowSelected = rowKeys.every(k => selectedCells.has(k));
            return (
              <tr key={floor}>
                {/* Floor label (sticky) */}
                <td
                  onClick={() => toggleRow(floor)}
                  title={`Select all on Floor ${floor}`}
                  className={`
                    sticky left-0 z-10 px-2 py-1.5 border-b border-r border-[#e2e8f0]
                    font-semibold cursor-pointer select-none transition whitespace-nowrap
                    ${rowSelected
                      ? 'bg-[#1e293b] text-white'
                      : 'bg-[#f1f5f9] text-[#475569] hover:bg-[#e2e8f0]'
                    }
                  `}
                >
                  Floor {floor}
                </td>

                {/* Building cells */}
                {buildings.map(building => {
                  const key        = cellKey(building, floor);
                  const cell       = cellMap.get(key);
                  const isSelected = selectedCells.has(key);
                  const hasErrors  = (cell?.errorCount ?? 0) > 0;
                  const allSaved   = !!cell && cell.rowCount > 0 &&
                    (cell.createdCount + cell.existingCount) === cell.rowCount;

                  return (
                    <td
                      key={key}
                      onClick={e => {
                        if ((e.target as HTMLElement).tagName === 'INPUT') return;
                        toggleCell(key);
                      }}
                      className={`
                        border-b border-r border-[#e2e8f0] p-1 align-top cursor-pointer
                        transition-colors min-w-[120px]
                        ${isSelected
                          ? 'bg-[#eff6ff]'
                          : hasErrors
                            ? 'bg-red-50 hover:bg-red-50'
                            : allSaved
                              ? 'bg-[#f0fdf4] hover:bg-[#f0fdf4]'
                              : 'hover:bg-[#f8fafc]'
                        }
                      `}
                    >
                      {/* Unit codes — keyboard-aware input */}
                      <CellInput
                        initialValue={cell?.units ?? ''}
                        building={building}
                        floor={floor}
                        isSelected={isSelected}
                        hasErrors={hasErrors}
                        onCommit={onCellUnits}
                      />

                      {/* Template badge */}
                      {cell?.template && (
                        <div className="mt-0.5">
                          <span className={`
                            inline-block px-1 py-0.5 text-[10px] font-medium rounded max-w-full truncate
                            ${isSelected
                              ? 'bg-[#dbeafe] text-[#1d4ed8]'
                              : 'bg-[#f1f5f9] text-[#475569]'
                            }
                          `}>
                            {shortTemplateLabel(cell.template)}
                            {cell.mirror ? ' ↔' : ''}
                            {cell.ada    ? ' ♿' : ''}
                          </span>
                        </div>
                      )}

                      {/* Post-submit status */}
                      {cell && (cell.createdCount > 0 || cell.existingCount > 0) && (
                        <div className="mt-0.5 leading-none">
                          {cell.createdCount > 0 && (
                            <span className="text-[10px] text-[#047857] font-medium">
                              ✓ {cell.createdCount}
                            </span>
                          )}
                          {cell.existingCount > 0 && (
                            <span className="text-[10px] text-[#94a3b8] ml-1">
                              {cell.existingCount} exist.
                            </span>
                          )}
                        </div>
                      )}

                      {/* Error badge */}
                      {hasErrors && (
                        <span className="block text-[10px] text-red-500 mt-0.5">
                          ⚠ {cell!.errorCount} issue{cell!.errorCount !== 1 ? 's' : ''}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
