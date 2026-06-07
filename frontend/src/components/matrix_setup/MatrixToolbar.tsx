/**
 * MatrixToolbar  (Phase 6)
 * Top bar for the matrix grid: add row, clear, submit, quick-fill template.
 */
import React, { useState } from 'react';
import { GridRow, MatrixBulkResponse } from '../../types/matrix';
import { TEMPLATE_OPTIONS } from './MatrixGrid';

function makeId(): string {
  return Math.random().toString(36).slice(2, 10);
}

interface Props {
  rows:          GridRow[];
  validRowCount: number;
  submitting:    boolean;
  lastResult:    MatrixBulkResponse | null;
  onAddRow:      () => void;
  onAddBatch:    (rows: GridRow[]) => void;
  onClear:       () => void;
  onSubmit:      () => void;
  onLoadExisting: () => void;
  loadingExisting: boolean;
}

export const MatrixToolbar: React.FC<Props> = ({
  rows, validRowCount, submitting, lastResult,
  onAddRow, onAddBatch, onClear, onSubmit, onLoadExisting, loadingExisting,
}) => {
  const [showQuickFill, setShowQuickFill] = useState(false);
  const [qfBuilding,    setQfBuilding]    = useState('A');
  const [qfFloorStart,  setQfFloorStart]  = useState('1');
  const [qfFloorEnd,    setQfFloorEnd]    = useState('10');
  const [qfUnitsPerFloor, setQfUnitsPerFloor] = useState('2');
  const [qfTemplate,    setQfTemplate]    = useState('SINGLE_VANITY');
  const [qfMirrorAlt,   setQfMirrorAlt]   = useState(false);
  const [qfError,       setQfError]       = useState('');

  function handleQuickFill() {
    setQfError('');
    const fStart = parseInt(qfFloorStart, 10);
    const fEnd   = parseInt(qfFloorEnd, 10);
    const uCount = parseInt(qfUnitsPerFloor, 10);
    if (!qfBuilding.trim())             { setQfError('Building is required.'); return; }
    if (isNaN(fStart) || isNaN(fEnd) || fStart > fEnd) { setQfError('Invalid floor range.'); return; }
    if (fEnd - fStart > 50)             { setQfError('Max 50 floors.'); return; }
    if (isNaN(uCount) || uCount < 1 || uCount > 20) { setQfError('Units per floor: 1–20.'); return; }
    if (!qfTemplate)                    { setQfError('Select a template.'); return; }

    const newRows: GridRow[] = [];
    for (let f = fStart; f <= fEnd; f++) {
      for (let u = 1; u <= uCount; u++) {
        const flatCode = `${f}${String(u).padStart(2, '0')}`;
        const mirror = qfMirrorAlt ? u % 2 === 0 : false;
        newRows.push({
          _id: makeId(), building: qfBuilding.trim(), floor: String(f),
          flat: flatCode, template: qfTemplate, mirror, ada: false,
        });
      }
    }
    onAddBatch(newRows);
    setShowQuickFill(false);
  }

  const canSubmit = validRowCount > 0 && !submitting;

  return (
    <div className="flex flex-col gap-2">
      {/* ── Primary actions row ─────────────────────────────────────── */}
      <div className="flex items-center gap-2 flex-wrap">

        <button
          type="button"
          onClick={onAddRow}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-white text-[#334155] border border-[#e2e8f0] rounded hover:bg-[#f8fafc] transition"
        >
          + Add Row
        </button>

        <button
          type="button"
          onClick={() => setShowQuickFill(s => !s)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-white text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition"
        >
          ⚡ Quick Fill
        </button>

        <button
          type="button"
          onClick={onLoadExisting}
          disabled={loadingExisting}
          title="Load units that already exist in this project"
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 transition disabled:opacity-50"
        >
          {loadingExisting ? '…' : '↓ Load Existing'}
        </button>

        <div className="flex-1" />

        {rows.length > 0 && (
          <>
            <button
              type="button"
              onClick={onClear}
              className="px-3 py-1.5 text-xs font-medium text-gray-500 border border-gray-200 rounded-md hover:bg-gray-50 transition"
            >
              Clear all
            </button>

            <button
              type="button"
              onClick={onSubmit}
              disabled={!canSubmit}
              className={`
                flex items-center gap-2 px-4 py-1.5 text-sm font-bold rounded-md transition
                ${canSubmit
                  ? 'bg-[#1e293b] text-white hover:bg-[#334155]'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }
              `}
            >
              {submitting ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  Save to Project
                  {validRowCount > 0 && (
                    <span className="text-xs font-normal opacity-80">({validRowCount} row{validRowCount !== 1 ? 's' : ''})</span>
                  )}
                </>
              )}
            </button>
          </>
        )}
      </div>

      {/* ── Quick Fill panel ──────────────────────────────────────────── */}
      {showQuickFill && (
        <div className="p-3 bg-[#f8fafc] border border-[#e2e8f0] rounded text-sm">
          <p className="text-xs font-semibold text-[#334155] uppercase tracking-wide mb-2.5">Quick Fill — Generate Rows</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-600">Building</label>
              <input value={qfBuilding} onChange={e => setQfBuilding(e.target.value)}
                placeholder="A" className="px-2 py-1 text-xs border border-[#cbd5e1] rounded outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6]" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-600">Floor from</label>
              <input type="number" min={1} value={qfFloorStart} onChange={e => setQfFloorStart(e.target.value)}
                className="px-2 py-1 text-xs border border-[#cbd5e1] rounded outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6]" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-600">Floor to</label>
              <input type="number" min={1} value={qfFloorEnd} onChange={e => setQfFloorEnd(e.target.value)}
                className="px-2 py-1 text-xs border border-[#cbd5e1] rounded outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6]" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-600">Units / floor</label>
              <input type="number" min={1} max={20} value={qfUnitsPerFloor} onChange={e => setQfUnitsPerFloor(e.target.value)}
                className="px-2 py-1 text-xs border border-[#cbd5e1] rounded outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6]" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-600">Template</label>
              <select value={qfTemplate} onChange={e => setQfTemplate(e.target.value)}
                className="px-2 py-1 text-xs border border-[#cbd5e1] rounded outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6]">
                {TEMPLATE_OPTIONS.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-600">Auto-mirror</label>
              <label className="flex items-center gap-1.5 mt-1.5 cursor-pointer">
                <input type="checkbox" checked={qfMirrorAlt} onChange={e => setQfMirrorAlt(e.target.checked)}
                  className="w-4 h-4 rounded border-[#cbd5e1] text-[#1e293b]" />
                <span className="text-xs text-gray-600">Even units mirrored</span>
              </label>
            </div>
          </div>
          {qfError && <p className="text-xs text-red-500 mt-2">{qfError}</p>}
          <div className="flex gap-2 mt-3">
            <button type="button" onClick={handleQuickFill}
              className="btn-primary text-xs px-4 py-1.5">
              Generate
            </button>
            <button type="button" onClick={() => setShowQuickFill(false)}
              className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded hover:bg-gray-50 transition">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* ── Last submit summary ───────────────────────────────────────── */}
      {lastResult && (
        <div className={`
          flex items-center gap-3 px-3 py-2 rounded-md text-sm
          ${lastResult.units_errored > 0 ? 'bg-yellow-50 border border-yellow-200' : 'bg-green-50 border border-green-200'}
        `}>
          <span className="text-lg">{lastResult.units_errored > 0 ? '⚠️' : '✅'}</span>
          <span className="text-green-700 font-medium">
            {lastResult.units_created} created
          </span>
          {lastResult.units_existing > 0 && (
            <span className="text-slate-500">{lastResult.units_existing} already existed</span>
          )}
          {lastResult.units_errored > 0 && (
            <span className="text-red-600">{lastResult.units_errored} errors</span>
          )}
          <span className="text-gray-400 text-xs ml-auto">
            {lastResult.buildings_total} bldg · {lastResult.floors_total} floors · {lastResult.unit_types_total} types
          </span>
        </div>
      )}
    </div>
  );
};
