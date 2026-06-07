/**
 * MatrixBulkActions  (Phase 6 → Phase 2 palette polish)
 * Duplicate Floor / Duplicate Building operations.
 *
 * Phase 2: indigo → slate, gray → StoneDesk palette, compact controls.
 */
import React, { useState } from 'react';
import { GridRow } from '../../types/matrix';

function makeId(): string {
  return Math.random().toString(36).slice(2, 10);
}

// ---------------------------------------------------------------------------
// Shared compact input style (StoneDesk .input-field equivalent but sized)
// ---------------------------------------------------------------------------
const compactInput = 'px-2 py-1 text-xs border border-[#cbd5e1] rounded bg-white text-[#1e293b] outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6] transition-all';

// ---------------------------------------------------------------------------
// Duplicate-floor panel
// ---------------------------------------------------------------------------

interface DuplicateFloorProps {
  rows:     GridRow[];
  onAppend: (newRows: GridRow[]) => void;
}

export function DuplicateFloor({ rows, onAppend }: DuplicateFloorProps) {
  const floors = Array.from(new Set(rows.map(r => r.floor))).sort();
  const [srcFloor,  setSrcFloor]  = useState(floors[0] ?? '');
  const [fromFloor, setFromFloor] = useState('');
  const [toFloor,   setToFloor]   = useState('');
  const [error,     setError]     = useState('');

  function execute() {
    setError('');
    const from = parseInt(fromFloor, 10);
    const to   = parseInt(toFloor,   10);
    if (!srcFloor)                              { setError('Pick a source floor.'); return; }
    if (isNaN(from) || isNaN(to) || from > to) { setError('Enter a valid floor range.'); return; }
    if (to - from > 50)                         { setError('Max 50 floors at once.'); return; }

    const templateRows = rows.filter(r => r.floor === srcFloor);
    if (!templateRows.length) { setError('No rows on that floor.'); return; }

    const newRows: GridRow[] = [];
    for (let f = from; f <= to; f++) {
      for (const tr of templateRows) {
        newRows.push({ ...tr, _id: makeId(), floor: String(f), _status: undefined, _error: undefined });
      }
    }
    onAppend(newRows);
  }

  return (
    <div className="flex flex-col gap-2 p-3 bg-[#f8fafc] rounded border border-[#e2e8f0]">
      <p className="text-[10px] font-bold text-[#475569] uppercase tracking-wider">Duplicate Floor</p>
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex flex-col gap-0.5">
          <label className="text-[10px] text-[#64748b]">Source floor</label>
          <select
            value={srcFloor}
            onChange={e => setSrcFloor(e.target.value)}
            className={compactInput}
          >
            {floors.map(f => <option key={f} value={f}>Floor {f}</option>)}
          </select>
        </div>
        <span className="text-[#94a3b8] pt-4 text-xs">→</span>
        <div className="flex flex-col gap-0.5">
          <label className="text-[10px] text-[#64748b]">From floor #</label>
          <input
            type="number" min={1} value={fromFloor}
            onChange={e => setFromFloor(e.target.value)}
            placeholder="2"
            className={`${compactInput} w-14`}
          />
        </div>
        <div className="flex flex-col gap-0.5">
          <label className="text-[10px] text-[#64748b]">To floor #</label>
          <input
            type="number" min={1} value={toFloor}
            onChange={e => setToFloor(e.target.value)}
            placeholder="10"
            className={`${compactInput} w-14`}
          />
        </div>
        <button
          type="button"
          onClick={execute}
          className="mt-auto btn-primary text-xs px-3 py-1"
        >
          Duplicate
        </button>
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Duplicate-building panel
// ---------------------------------------------------------------------------

interface DuplicateBuildingProps {
  rows:     GridRow[];
  onAppend: (newRows: GridRow[]) => void;
}

export function DuplicateBuilding({ rows, onAppend }: DuplicateBuildingProps) {
  const buildings = Array.from(new Set(rows.map(r => r.building))).sort();
  const [srcBuilding,  setSrcBuilding]  = useState(buildings[0] ?? '');
  const [destBuilding, setDestBuilding] = useState('');
  const [error,        setError]        = useState('');

  function execute() {
    setError('');
    if (!srcBuilding)                          { setError('Pick a source building.'); return; }
    if (!destBuilding.trim())                  { setError('Enter a destination building code.'); return; }
    if (destBuilding.trim() === srcBuilding)   { setError('Destination must differ from source.'); return; }

    const templateRows = rows.filter(r => r.building === srcBuilding);
    if (!templateRows.length) { setError('No rows in that building.'); return; }

    const newRows: GridRow[] = templateRows.map(tr => ({
      ...tr,
      _id:      makeId(),
      building: destBuilding.trim(),
      _status:  undefined,
      _error:   undefined,
    }));
    onAppend(newRows);
    setDestBuilding('');
  }

  return (
    <div className="flex flex-col gap-2 p-3 bg-[#f8fafc] rounded border border-[#e2e8f0]">
      <p className="text-[10px] font-bold text-[#475569] uppercase tracking-wider">Copy Building</p>
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex flex-col gap-0.5">
          <label className="text-[10px] text-[#64748b]">Source</label>
          <select
            value={srcBuilding}
            onChange={e => setSrcBuilding(e.target.value)}
            className={compactInput}
          >
            {buildings.map(b => <option key={b} value={b}>Building {b}</option>)}
          </select>
        </div>
        <span className="text-[#94a3b8] pt-4 text-xs">→</span>
        <div className="flex flex-col gap-0.5">
          <label className="text-[10px] text-[#64748b]">New building code</label>
          <input
            value={destBuilding}
            onChange={e => setDestBuilding(e.target.value)}
            placeholder="B"
            className={`${compactInput} w-20`}
          />
        </div>
        <button
          type="button"
          onClick={execute}
          className="mt-auto btn-primary text-xs px-3 py-1"
        >
          Copy
        </button>
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Combined panel (collapsible)
// ---------------------------------------------------------------------------

interface MatrixBulkActionsProps {
  rows:     GridRow[];
  onAppend: (newRows: GridRow[]) => void;
}

export const MatrixBulkActions: React.FC<MatrixBulkActionsProps> = ({ rows, onAppend }) => {
  const [open, setOpen] = useState(false);
  const hasRows = rows.length > 0;

  return (
    <div>
      <button
        type="button"
        disabled={!hasRows}
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#475569] border border-[#e2e8f0] rounded hover:bg-[#f8fafc] transition disabled:opacity-40"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
        Bulk Fill
        <span className="ml-0.5 text-[#94a3b8]">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <DuplicateFloor rows={rows} onAppend={onAppend} />
          <DuplicateBuilding rows={rows} onAppend={onAppend} />
        </div>
      )}
    </div>
  );
};
