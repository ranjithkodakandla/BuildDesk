/**
 * MatrixSetupPanel  (Phase 8.5 — Hierarchical Matrix Redesign)
 *
 * Redesigned around a Building → Floor → Units model.
 * Primary view: cross-tab grid (buildings as columns, floors as rows).
 * Each cell holds comma-separated unit codes for that intersection.
 *
 * Underlying data: flat GridRow[] — backend API unchanged.
 *
 * Preserved features:
 *  - CSV import/export
 *  - Undo (single-level)
 *  - Autosave draft
 *  - Validation (per flat row)
 *  - Bulk Fill (copy building/floor)
 *  - Generator (replaces Quick Fill — same power, multi-building)
 *  - Excel paste
 *  - Connected workflow (workflowStore refresh)
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Project } from '../types/hierarchy';
import { GridRow, MatrixBulkResponse, MatrixExportRow } from '../types/matrix';
import { matrixApi } from '../api/matrix';
import { HierarchicalGrid, cellKey } from './matrix_setup/HierarchicalGrid';
import { MatrixBulkActions }  from './matrix_setup/MatrixBulkActions';
import { MatrixImportExport, parseTextToRows, ParseResult, ImportError } from './matrix_setup/MatrixImportExport';
import { validateRows }       from './matrix_setup/MatrixValidation';
import { TEMPLATE_OPTIONS }   from './matrix_setup/MatrixGrid';
import { useWorkflowStore }   from '../store/workflowStore';

// ---------------------------------------------------------------------------
// Draft persistence helpers
// ---------------------------------------------------------------------------

const _DRAFT_KEY = (pid: string) => `bd_matrix_draft_v1_${pid}`;

function loadDraft(projectId: string): GridRow[] | null {
  try {
    const v = localStorage.getItem(_DRAFT_KEY(projectId));
    return v ? (JSON.parse(v) as GridRow[]) : null;
  } catch { return null; }
}

function saveDraft(projectId: string, rows: GridRow[]): void {
  try {
    rows.length === 0
      ? localStorage.removeItem(_DRAFT_KEY(projectId))
      : localStorage.setItem(_DRAFT_KEY(projectId), JSON.stringify(rows));
  } catch { /* storage full */ }
}

function clearDraft(projectId: string): void {
  try { localStorage.removeItem(_DRAFT_KEY(projectId)); } catch { /* ignore */ }
}

// ---------------------------------------------------------------------------
// Row factory helpers
// ---------------------------------------------------------------------------

function makeId(): string {
  return Math.random().toString(36).slice(2, 10);
}

function gridRowFromExport(r: MatrixExportRow): GridRow {
  return {
    _id:      makeId(),
    building: r.building,
    floor:    r.floor,
    flat:     r.flat,
    template: r.template,
    mirror:   r.mirror,
    ada:      r.ada,
    _unit_id: r.unit_id ?? undefined,
    _status:  'existing',
  };
}

// ---------------------------------------------------------------------------
// Generator helpers
// ---------------------------------------------------------------------------

function parseList(input: string): string[] {
  return input.split(',').map(s => s.trim()).filter(Boolean);
}

function parseFloors(input: string): string[] {
  const result: string[] = [];
  for (const part of input.split(',').map(s => s.trim()).filter(Boolean)) {
    const m = part.match(/^(\d+)-(\d+)$/);
    if (m) {
      const from = parseInt(m[1], 10), to = parseInt(m[2], 10);
      if (from <= to && to - from <= 99) {
        for (let i = from; i <= to; i++) result.push(String(i));
      }
    } else {
      result.push(part);
    }
  }
  return result;
}

function generateUnitCode(floor: string, unitIndex: number): string {
  const floorNum = parseInt(floor, 10);
  return !isNaN(floorNum)
    ? `${floorNum}${String(unitIndex).padStart(2, '0')}`
    : `${floor}-${unitIndex}`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  project: Project;
  onNavigateToBuilder?: (templateId: string) => void;
  onViewUnits?: () => void;
}

export const MatrixSetupPanel: React.FC<Props> = ({ project, onNavigateToBuilder, onViewUnits }) => {
  const pid = project.project_id;

  // ── Core row state ────────────────────────────────────────────────────────
  const [rows,            setRows]            = useState<GridRow[]>(() => loadDraft(pid) ?? []);
  const [submitting,      setSubmitting]      = useState(false);
  const [lastResult,      setLastResult]      = useState<MatrixBulkResponse | null>(null);
  const [loadingExisting, setLoadingExisting] = useState(false);
  const [globalError,     setGlobalError]     = useState<string | null>(null);
  const [undoBuffer,      setUndoBuffer]      = useState<GridRow[] | null>(null);
  const [importErrors,    setImportErrors]    = useState<ImportError[]>([]);
  const [draftRestored,   setDraftRestored]   = useState<boolean>(
    () => (loadDraft(pid)?.length ?? 0) > 0,
  );

  // ── Grid selection + assignment ───────────────────────────────────────────
  const [selectedCells,  setSelectedCells]  = useState<Set<string>>(new Set());
  const [assignTemplate, setAssignTemplate] = useState('');
  const [assignMirror,   setAssignMirror]   = useState(false);
  const [assignAda,      setAssignAda]      = useState(false);

  // ── Generator bar state ───────────────────────────────────────────────────
  const [genBuildings,   setGenBuildings]   = useState('1, 2, 3');
  const [genFloors,      setGenFloors]      = useState('1, 2, 3, 4, 5');
  const [genUnitsFloor,  setGenUnitsFloor]  = useState('2');
  const [genTemplate,    setGenTemplate]    = useState('SINGLE_VANITY');
  const [genMirrorAlt,   setGenMirrorAlt]   = useState(false);
  const [genError,       setGenError]       = useState('');
  // Always show generator when no rows exist; user can collapse once they have data
  const [genExpanded, setGenExpanded] = useState(() => (loadDraft(pid)?.length ?? 0) === 0);

  // ── Workflow store ────────────────────────────────────────────────────────
  const workflowRefresh = useWorkflowStore(s => s.refresh);

  // ── Autosave draft (debounced 1.5s) ──────────────────────────────────────
  const autosaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    autosaveTimer.current = setTimeout(() => saveDraft(pid, rows), 1500);
    return () => { if (autosaveTimer.current) clearTimeout(autosaveTimer.current); };
  }, [rows, pid]);

  // ── Excel / clipboard paste at panel level ────────────────────────────────
  useEffect(() => {
    function onPaste(e: ClipboardEvent) {
      const target = document.activeElement;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) return;
      const text = e.clipboardData?.getData('text/plain') ?? '';
      if (!text.includes('\t') && !text.includes('\n')) return;
      e.preventDefault();
      const result = parseTextToRows(text);
      if (result.rows.length) setRows(prev => [...prev, ...result.rows]);
      if (result.errors.length) setImportErrors(result.errors);
    }
    document.addEventListener('paste', onPaste);
    return () => document.removeEventListener('paste', onPaste);
  }, []);

  // ── Validation ────────────────────────────────────────────────────────────
  const validation = validateRows(rows);
  const validRowCount = rows.filter(r => (validation.get(r._id)?.valid ?? false)).length;

  // ── Generator ─────────────────────────────────────────────────────────────
  function handleGenerate() {
    setGenError('');
    const buildings = parseList(genBuildings);
    const floors    = parseFloors(genFloors);
    const nUnits    = parseInt(genUnitsFloor, 10);

    if (!buildings.length)                  { setGenError('Enter at least one building (e.g. 1, 2, 3)'); return; }
    if (!floors.length)                     { setGenError('Enter floors (e.g. 1-5 or 1, 2, 3)'); return; }
    if (isNaN(nUnits) || nUnits < 1 || nUnits > 20) { setGenError('Units per floor: 1–20.'); return; }
    if (!genTemplate)                       { setGenError('Select a template.'); return; }
    if (buildings.length * floors.length * nUnits > 500) {
      setGenError('Max 500 units at once. Reduce buildings × floors × units/floor.');
      return;
    }

    const newRows: GridRow[] = [];
    for (const building of buildings) {
      for (const floor of floors) {
        for (let u = 1; u <= nUnits; u++) {
          newRows.push({
            _id: makeId(),
            building,
            floor,
            flat:     generateUnitCode(floor, u),
            template: genTemplate,
            mirror:   genMirrorAlt ? u % 2 === 0 : false,
            ada:      false,
          });
        }
      }
    }

    if (rows.length > 0) {
      if (!window.confirm(
        `This will replace ${rows.length} existing rows with ${newRows.length} generated rows.\n\nContinue?`
      )) return;
    }

    setUndoBuffer(rows);
    setRows(newRows);
    setSelectedCells(new Set());
    setLastResult(null);
    setGlobalError(null);
    setDraftRestored(false);
  }

  // ── Cell units change ─────────────────────────────────────────────────────
  const handleCellUnits = useCallback((building: string, floor: string, newUnitsStr: string) => {
    const unitCodes = newUnitsStr.split(',').map(s => s.trim()).filter(Boolean);
    setRows(prev => {
      const existing = prev.filter(r => r.building === building && r.floor === floor);
      const template  = existing[0]?.template ?? '';
      const mirror    = existing[0]?.mirror ?? false;
      const ada       = existing[0]?.ada ?? false;
      const others    = prev.filter(r => !(r.building === building && r.floor === floor));
      const newRows   = unitCodes.map(flat => ({
        _id: makeId(), building, floor, flat, template, mirror, ada,
      }));
      return [...others, ...newRows];
    });
  }, []);

  // ── Assignment: apply template/mirror/ADA to selected cells ──────────────
  function applyAssignment() {
    if (!assignTemplate) return;
    setUndoBuffer(rows);
    setRows(prev => prev.map(row => {
      const key = cellKey(row.building, row.floor);
      if (selectedCells.has(key)) {
        return { ...row, template: assignTemplate, mirror: assignMirror, ada: assignAda };
      }
      return row;
    }));
    setSelectedCells(new Set());
  }

  // ── Undo ──────────────────────────────────────────────────────────────────
  const captureUndo = useCallback(() => {
    setRows(prev => { setUndoBuffer(prev); return prev; });
  }, []);

  function handleUndo() {
    if (undoBuffer) { setRows(undoBuffer); setUndoBuffer(null); }
  }

  // ── Clear all ─────────────────────────────────────────────────────────────
  function clearAll() {
    setRows([]); setSelectedCells(new Set()); setLastResult(null);
    setGlobalError(null); setUndoBuffer(null); setDraftRestored(false);
    clearDraft(pid);
  }

  // ── Load existing units from project ─────────────────────────────────────
  async function loadExisting() {
    setLoadingExisting(true);
    try {
      const resp = await matrixApi.getMatrix(project.project_id);
      setRows(resp.rows.map(r => gridRowFromExport(r)));
      setSelectedCells(new Set());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setGlobalError(`Failed to load existing units: ${msg}`);
    } finally {
      setLoadingExisting(false);
    }
  }

  // ── Submit ────────────────────────────────────────────────────────────────
  async function submit() {
    setGlobalError(null);
    const toSubmit = rows.filter(r => validation.get(r._id)?.valid);
    if (!toSubmit.length) return;
    setSubmitting(true);
    try {
      const result = await matrixApi.bulkMatrix(project.project_id, {
        rows: toSubmit.map(r => ({
          building: r.building, floor: r.floor, flat: r.flat,
          template: r.template, mirror: r.mirror, ada: r.ada,
        })),
      });
      const byKey = new Map<string, (typeof result.results)[0]>();
      result.results.forEach((res, i) => {
        const row = toSubmit[i];
        if (row) byKey.set(row._id, res);
      });
      setRows(prev => prev.map(r => {
        const res = byKey.get(r._id);
        if (!res) return r;
        return { ...r, _status: res.status, _error: res.error ?? undefined, _unit_id: res.unit_id ?? undefined };
      }));
      setLastResult(result);
      clearDraft(pid);
      setDraftRestored(false);
      // Refresh workflow store so tab badges update
      workflowRefresh(pid);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setGlobalError(`Save failed — ${msg}. Your work is preserved. Try again.`);
    } finally {
      setSubmitting(false);
    }
  }

  // ── CSV import ────────────────────────────────────────────────────────────
  function handleImport(result: ParseResult) {
    if (result.rows.length > 0) setRows(prev => [...prev, ...result.rows]);
    setImportErrors(result.errors);
  }

  // ── Stats ─────────────────────────────────────────────────────────────────
  const numBuildings = new Set(rows.map(r => r.building).filter(Boolean)).size;
  const numFloors    = new Set(rows.map(r => r.floor).filter(Boolean)).size;

  // ── Assignment panel prefill when selection changes ───────────────────────
  useEffect(() => {
    if (selectedCells.size === 0) return;
    // Prefill from first selected cell's existing rows
    const firstKey = [...selectedCells][0];
    const [b, f] = firstKey.split('::');
    const cellRows = rows.filter(r => r.building === b && r.floor === f);
    if (cellRows.length > 0) {
      setAssignTemplate(cellRows[0].template || '');
      setAssignMirror(cellRows[0].mirror);
      setAssignAda(cellRows[0].ada);
    }
  }, [selectedCells]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-4">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-[#1e293b]">Project Setup</h2>
          <p className="text-xs text-[#64748b] mt-0.5">Building · floor · flat. Select cells to assign templates.</p>
        </div>
        <MatrixImportExport
          rows={rows}
          projectId={pid}
          onImport={handleImport}
        />
      </div>

      {/* ── Generator bar ──────────────────────────────────────────────── */}
      <div className="bg-white border border-[#e2e8f0] rounded-md overflow-hidden">
        <button
          type="button"
          onClick={() => setGenExpanded(e => !e)}
          className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-[#f8fafc] transition"
        >
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-[#334155]">Generate Grid</span>
            <span className="text-xs text-[#94a3b8]">
              {rows.length > 0
                ? `${rows.length} units · ${numBuildings} bldg · ${numFloors} floor${numFloors !== 1 ? 's' : ''}`
                : 'buildings, floors, units/floor'}
            </span>
          </div>
          <span className="text-[#94a3b8] text-xs">{genExpanded ? '▲' : '▼'}</span>
        </button>

        {genExpanded && (
          <div className="px-3 pb-3 space-y-2.5 border-t border-[#f1f5f9]">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 pt-2.5">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-[#64748b]">Buildings</label>
                <input
                  value={genBuildings}
                  onChange={e => setGenBuildings(e.target.value)}
                  placeholder="1, 2, 3"
                  className="input-field text-xs py-1.5"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-[#64748b]">Floors <span className="text-[#94a3b8]">(or 1-10)</span></label>
                <input
                  value={genFloors}
                  onChange={e => setGenFloors(e.target.value)}
                  placeholder="1, 2, 3, 4, 5"
                  className="input-field text-xs py-1.5"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-[#64748b]">Units / floor</label>
                <input
                  type="number" min={1} max={20}
                  value={genUnitsFloor}
                  onChange={e => setGenUnitsFloor(e.target.value)}
                  className="input-field text-xs py-1.5"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-[#64748b]">Template</label>
                <select
                  value={genTemplate}
                  onChange={e => setGenTemplate(e.target.value)}
                  className="input-field text-xs py-1.5"
                >
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
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-[#64748b]">Auto-mirror</label>
                <label className="flex items-center gap-2 mt-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={genMirrorAlt}
                    onChange={e => setGenMirrorAlt(e.target.checked)}
                    className="w-3.5 h-3.5 rounded border-[#cbd5e1] text-[#1e293b]"
                  />
                  <span className="text-xs text-[#475569]">Even units mirrored</span>
                </label>
              </div>
            </div>
            {genError && <p className="text-xs text-red-600">{genError}</p>}
            <button
              type="button"
              onClick={handleGenerate}
              className="btn-primary text-xs px-4 py-1.5"
            >
              Generate Grid →
            </button>
          </div>
        )}
      </div>

      {/* ── Draft restored banner ───────────────────────────────────────── */}
      {draftRestored && rows.length > 0 && (
        <div className="px-3 py-2 bg-[#fffbeb] border border-[#fcd34d] rounded text-xs text-[#92400e] flex items-center justify-between">
          <span>Draft restored — {rows.length} unit{rows.length !== 1 ? 's' : ''} from last session, not saved.</span>
          <button onClick={() => setDraftRestored(false)} className="ml-2 text-[#b45309] hover:text-[#92400e] font-bold leading-none" aria-label="Dismiss">×</button>
        </div>
      )}

      {/* ── Undo banner ────────────────────────────────────────────────── */}
      {undoBuffer !== null && (
        <div className="px-3 py-2 bg-[#f1f5f9] border border-[#cbd5e1] rounded text-xs text-[#334155] flex items-center justify-between">
          <span>Action applied.</span>
          <button onClick={handleUndo} className="ml-2 px-2 py-0.5 text-xs font-bold bg-[#1e293b] text-white rounded hover:bg-[#334155] transition">
            ↩ Undo
          </button>
        </div>
      )}

      {/* ── Global error ────────────────────────────────────────────────── */}
      {globalError && (
        <div className="px-3 py-2 bg-red-50 border border-red-200 rounded text-xs text-red-700 flex justify-between items-start">
          <div>
            <p className="font-medium">{globalError}</p>
            <button onClick={submit} className="mt-1 text-red-600 underline hover:text-red-800">Retry →</button>
          </div>
          <button onClick={() => setGlobalError(null)} className="ml-3 text-red-400 hover:text-red-600 font-bold leading-none" aria-label="Dismiss">×</button>
        </div>
      )}

      {/* ── CSV import errors ───────────────────────────────────────────── */}
      {importErrors.length > 0 && (
        <div className="rounded border border-amber-200 bg-[#fffbeb] p-3">
          <div className="flex items-center justify-between mb-1.5">
            <p className="text-xs font-bold text-amber-800">
              {importErrors.length} import issue{importErrors.length !== 1 ? 's' : ''} — rows skipped
            </p>
            <button onClick={() => setImportErrors([])} className="text-amber-400 hover:text-amber-700 font-bold leading-none" aria-label="Dismiss">×</button>
          </div>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {importErrors.slice(0, 15).map((err, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-amber-700 bg-white rounded px-2 py-1 border border-amber-100">
                <span className="font-bold shrink-0 text-amber-500">Row {err.sourceRow}</span>
                <span className="font-semibold shrink-0">{err.column}</span>
                {err.value && <span className="text-[#64748b] shrink-0">"{err.value}"</span>}
                <span>{err.message}</span>
              </div>
            ))}
            {importErrors.length > 15 && (
              <p className="text-xs text-amber-600 text-center pt-1">…and {importErrors.length - 15} more</p>
            )}
          </div>
        </div>
      )}

      {/* ── Hierarchical grid ───────────────────────────────────────────── */}
      <div className="bg-white rounded border border-[#e2e8f0] overflow-hidden">
        <HierarchicalGrid
          rows={rows}
          validation={validation}
          selectedCells={selectedCells}
          onSelectionChange={setSelectedCells}
          onCellUnits={handleCellUnits}
        />
      </div>

      {/* ── Assignment panel (shown when cells selected) ─────────────────── */}
      {selectedCells.size > 0 && (
        <div className="bg-[#f1f5f9] border border-[#cbd5e1] rounded px-3 py-2.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="text-xs font-semibold text-[#334155]">
              {selectedCells.size} cell{selectedCells.size !== 1 ? 's' : ''} selected
            </span>

            <div className="flex items-center gap-1.5">
              <span className="text-xs text-[#64748b]">Template:</span>
              <select
                value={assignTemplate}
                onChange={e => setAssignTemplate(e.target.value)}
                className="input-field text-xs py-1 min-w-[140px]"
              >
                <option value="">Choose…</option>
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
            </div>

            <label className="flex items-center gap-1.5 cursor-pointer text-xs text-[#475569]">
              <input
                type="checkbox"
                checked={assignMirror}
                onChange={e => setAssignMirror(e.target.checked)}
                className="w-3.5 h-3.5 rounded border-[#cbd5e1] text-[#1e293b]"
              />
              Mirror
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer text-xs text-[#475569]">
              <input
                type="checkbox"
                checked={assignAda}
                onChange={e => setAssignAda(e.target.checked)}
                className="w-3.5 h-3.5 rounded border-[#cbd5e1] text-[#1e293b]"
              />
              ADA
            </label>

            <button
              type="button"
              onClick={applyAssignment}
              disabled={!assignTemplate}
              className="btn-primary text-xs px-3 py-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Apply to {selectedCells.size}
            </button>

            {onNavigateToBuilder && assignTemplate && (
              <button
                type="button"
                onClick={() => onNavigateToBuilder(assignTemplate)}
                className="text-xs text-[#3b82f6] hover:text-[#1d4ed8] transition"
                title="Open this template in Basic Builder"
              >
                Open in Builder →
              </button>
            )}

            <button
              type="button"
              onClick={() => setSelectedCells(new Set())}
              className="ml-auto text-xs text-[#94a3b8] hover:text-[#475569] transition"
              aria-label="Clear selection"
            >
              Clear ×
            </button>
          </div>
        </div>
      )}

      {/* ── Stats + submit bar ──────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2">
        {rows.length > 0 && (
          <div className="flex gap-3 text-xs text-[#64748b]">
            <span><b className="text-[#1e293b]">{rows.length}</b> units</span>
            <span><b className="text-[#1e293b]">{numBuildings}</b> bldg</span>
            <span><b className="text-[#1e293b]">{numFloors}</b> floor{numFloors !== 1 ? 's' : ''}</span>
            {validRowCount < rows.length && (
              <span className="text-amber-600"><b>{rows.length - validRowCount}</b> need attention</span>
            )}
          </div>
        )}

        <div className="flex-1" />

        <button
          type="button"
          onClick={loadExisting}
          disabled={loadingExisting}
          className="px-2.5 py-1.5 text-xs text-[#64748b] border border-[#e2e8f0] rounded hover:bg-[#f8fafc] transition disabled:opacity-50"
        >
          {loadingExisting ? '…' : '↓ Load Saved'}
        </button>

        {rows.length > 0 && (
          <button
            type="button"
            onClick={clearAll}
            className="px-2.5 py-1.5 text-xs text-[#64748b] border border-[#e2e8f0] rounded hover:bg-[#f8fafc] transition"
          >
            Clear all
          </button>
        )}

        {rows.length > 0 && (
          <button
            type="button"
            onClick={submit}
            disabled={validRowCount === 0 || submitting}
            className={`
              flex items-center gap-1.5 px-4 py-1.5 text-xs font-bold rounded transition
              ${validRowCount > 0 && !submitting
                ? 'bg-[#1e293b] text-white hover:bg-[#334155]'
                : 'bg-[#f1f5f9] text-[#94a3b8] cursor-not-allowed'
              }
            `}
          >
            {submitting ? (
              <>
                <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Saving…
              </>
            ) : (
              <>
                Save to Project
                {validRowCount > 0 && (
                  <span className="font-normal opacity-70">({validRowCount})</span>
                )}
              </>
            )}
          </button>
        )}
      </div>

      {/* ── Submit result banner ────────────────────────────────────────── */}
      {lastResult && (
        <div className={`flex items-center gap-2.5 px-3 py-2 rounded text-xs
          ${lastResult.units_errored > 0
            ? 'bg-amber-50 border border-amber-200 text-amber-800'
            : 'bg-[#ecfdf5] border border-[#6ee7b7] text-[#047857]'
          }`}>
          <span className="font-semibold">{lastResult.units_created} created</span>
          {lastResult.units_existing > 0 && (
            <span className="text-[#64748b]">{lastResult.units_existing} existing</span>
          )}
          {lastResult.units_errored > 0 && (
            <span className="text-red-600">{lastResult.units_errored} errors</span>
          )}
          <span className="text-[#94a3b8] ml-auto">
            {lastResult.buildings_total} bldg · {lastResult.floors_total} floors
          </span>
        </div>
      )}

      {/* ── Bulk Fill (copy building/floor) ─────────────────────────────── */}
      {rows.length > 0 && (
        <MatrixBulkActions
          rows={rows}
          onAppend={newRows => {
            captureUndo();
            setRows(prev => [...prev, ...newRows]);
          }}
        />
      )}

      {/* ── Hint + unit schedule link ───────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-[#94a3b8]">Ctrl+V / ⌘+V to paste from Excel · Submit is idempotent</p>
        {rows.length > 0 && onViewUnits && (
          <button
            type="button"
            onClick={onViewUnits}
            className="text-xs text-[#94a3b8] hover:text-[#3b82f6] transition underline shrink-0 ml-4"
          >
            View unit schedule →
          </button>
        )}
      </div>
    </div>
  );
};
