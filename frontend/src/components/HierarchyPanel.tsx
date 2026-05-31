import React, { useEffect, useState } from 'react';
import { Project, UnitStatus, UnitType, Unit, UnitVariant } from '../types/hierarchy';
import { projectsApi } from '../api/projects';
import { ImportModal } from './ImportModal';

interface Props {
  project: Project;
}

export const HierarchyPanel: React.FC<Props> = ({ project }) => {
  const [unitTypes, setUnitTypes] = useState<UnitType[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [loading, setLoading] = useState(true);
  const [showImportModal, setShowImportModal] = useState(false);

  // Selection for bulk operations
  const [selectedUnitIds, setSelectedUnitIds] = useState<string[]>([]);
  const [expandedTypeIds, setExpandedTypeIds] = useState<Set<string>>(new Set());

  // Inline quick-assign: which unit is open
  const [quickAssignUnitId, setQuickAssignUnitId] = useState<string | null>(null);

  // Add type form (always visible in sidebar — not hidden)
  const [newTypeCode, setNewTypeCode] = useState('');
  const [newTypeName, setNewTypeName] = useState('');
  const [addTypeWorking, setAddTypeWorking] = useState(false);

  // Bulk generate form
  const [showBulkGenerate, setShowBulkGenerate] = useState(false);
  const [bulkPrefix, setBulkPrefix] = useState('');
  const [bulkStart, setBulkStart] = useState('');
  const [bulkEnd, setBulkEnd] = useState('');
  const [bulkType, setBulkType] = useState('');
  const [bulkWorking, setBulkWorking] = useState(false);

  // Bulk update (applies to selectedUnitIds)
  const [bulkAssignType, setBulkAssignType] = useState('');
  const [bulkVariant, setBulkVariant] = useState<UnitVariant>(UnitVariant.STANDARD);
  const [bulkStatus] = useState<UnitStatus>(UnitStatus.ACTIVE);
  const [updateWorking, setUpdateWorking] = useState(false);

  // Search / filter
  const [search, setSearch] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [ut, u] = await Promise.all([
        projectsApi.listUnitTypes(project.project_id),
        projectsApi.listUnits(project.project_id),
      ]);
      setUnitTypes(ut);
      setUnits(u);
      setSelectedUnitIds((sel) => sel.filter((id) => u.some((unit) => unit.unit_id === id)));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [project.project_id]);

  // ── helpers ────────────────────────────────────────────────────────────────

  const toggleExpanded = (typeId: string) =>
    setExpandedTypeIds((prev) => {
      const next = new Set(prev);
      next.has(typeId) ? next.delete(typeId) : next.add(typeId);
      return next;
    });

  const toggleUnit = (unitId: string) =>
    setSelectedUnitIds((cur) =>
      cur.includes(unitId) ? cur.filter((id) => id !== unitId) : [...cur, unitId]
    );

  const toggleTypeUnits = (typeId: string) => {
    const typeUnits = units.filter((u) => u.unit_type_id === typeId).map((u) => u.unit_id);
    const allSelected = typeUnits.every((id) => selectedUnitIds.includes(id));
    setSelectedUnitIds((cur) =>
      allSelected
        ? cur.filter((id) => !typeUnits.includes(id))
        : Array.from(new Set([...cur, ...typeUnits]))
    );
  };

  const handleAddType = async () => {
    if (!newTypeCode.trim()) return;
    setAddTypeWorking(true);
    try {
      await projectsApi.createUnitType(project.project_id, {
        code: newTypeCode.trim(),
        name: newTypeName.trim() || newTypeCode.trim(),
        is_mirror: newTypeCode.toUpperCase().includes('MIR'),
        is_ada: newTypeCode.toUpperCase().includes('ADA'),
        sort_order: unitTypes.length + 1,
      });
      setNewTypeCode('');
      setNewTypeName('');
      await loadData();
    } catch (e) { console.error(e); }
    finally { setAddTypeWorking(false); }
  };

  const handleBulkGenerate = async () => {
    const start = parseInt(bulkStart, 10);
    const end   = parseInt(bulkEnd, 10);
    if (!Number.isFinite(start) || !Number.isFinite(end) || start > end) return;
    setBulkWorking(true);
    try {
      await projectsApi.bulkCreateUnits(project.project_id, {
        start_number: start,
        end_number: end,
        prefix: bulkPrefix,
        unit_type_id: bulkType || undefined,
      });
      setBulkStart('');
      setBulkEnd('');
      setShowBulkGenerate(false);
      await loadData();
    } catch (e) { console.error(e); }
    finally { setBulkWorking(false); }
  };

  const handleBulkUpdate = async () => {
    if (selectedUnitIds.length === 0) return;
    setUpdateWorking(true);
    try {
      await projectsApi.bulkUpdateUnits(project.project_id, {
        unit_ids: selectedUnitIds,
        unit_type_id: bulkAssignType || undefined,
        variant: bulkVariant,
        status: bulkStatus,
      });
      setSelectedUnitIds([]);
      await loadData();
    } catch (e) { console.error(e); }
    finally { setUpdateWorking(false); }
  };

  // Quick-assign a single unit inline
  const handleQuickAssign = async (unitId: string, typeId: string) => {
    try {
      await projectsApi.bulkUpdateUnits(project.project_id, {
        unit_ids: [unitId],
        unit_type_id: typeId || undefined,
        variant: UnitVariant.STANDARD,
        status: UnitStatus.ACTIVE,
      });
      setQuickAssignUnitId(null);
      await loadData();
    } catch (e) { console.error(e); }
  };

  // ── derived data ───────────────────────────────────────────────────────────

  const untypedUnits = units.filter((u) => !u.unit_type_id);
  const assignedCount = units.length - untypedUnits.length;

  const filteredUnits = (typeId: string) => {
    const base = units.filter((u) => u.unit_type_id === typeId);
    return search ? base.filter((u) => u.code.toLowerCase().includes(search.toLowerCase())) : base;
  };

  const filteredUntyped = search
    ? untypedUnits.filter((u) => u.code.toLowerCase().includes(search.toLowerCase()))
    : untypedUnits;

  // ── loading state ──────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-16 bg-gray-100 rounded-2xl" />
        <div className="h-40 bg-gray-100 rounded-2xl" />
        <div className="h-40 bg-gray-100 rounded-2xl" />
      </div>
    );
  }

  // ── empty state ────────────────────────────────────────────────────────────

  if (units.length === 0 && unitTypes.length === 0) {
    return (
      <div className="max-w-2xl space-y-5">
        <div className="bg-white rounded-2xl border border-dashed border-gray-300 p-12 text-center">
          <div className="text-4xl mb-3">🏠</div>
          <h3 className="text-lg font-bold text-gray-900 mb-2">No units yet</h3>
          <p className="text-sm text-gray-500 mb-6 max-w-xs mx-auto">
            Import a spreadsheet with your unit numbers to get started. You can assign stone types after importing.
          </p>
          <div className="flex justify-center gap-3 flex-wrap">
            <button
              onClick={() => setShowImportModal(true)}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow transition"
            >
              Import Unit Schedule
            </button>
            <button
              onClick={() => setShowBulkGenerate(true)}
              className="px-6 py-3 border border-gray-300 text-gray-700 font-medium rounded-xl hover:bg-gray-50 transition"
            >
              Generate Units Manually
            </button>
          </div>
        </div>

        {showBulkGenerate && (
          <BulkGenerateCard
            unitTypes={unitTypes}
            bulkPrefix={bulkPrefix} setBulkPrefix={setBulkPrefix}
            bulkStart={bulkStart}   setBulkStart={setBulkStart}
            bulkEnd={bulkEnd}       setBulkEnd={setBulkEnd}
            bulkType={bulkType}     setBulkType={setBulkType}
            bulkWorking={bulkWorking}
            onGenerate={handleBulkGenerate}
            onCancel={() => setShowBulkGenerate(false)}
          />
        )}
        {showImportModal && (
          <ImportModal projectId={project.project_id} onClose={() => { setShowImportModal(false); loadData(); }} />
        )}
      </div>
    );
  }

  // ── main layout: left column (units) + right column (tools) ───────────────

  return (
    <div className="flex gap-5 items-start max-w-7xl">

      {/* ══ LEFT: unit list ═══════════════════════════════════════════════ */}
      <div className="flex-1 min-w-0 space-y-4">

        {/* Summary + search bar */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm px-5 py-3 flex items-center gap-4 flex-wrap">
          {/* Progress */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-1">
              <span className="font-bold text-gray-900">{units.length} units total</span>
              {untypedUnits.length > 0 ? (
                <span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-xs font-bold rounded-full">
                  {untypedUnits.length} unassigned
                </span>
              ) : (
                <span className="px-2 py-0.5 bg-green-100 text-green-800 text-xs font-bold rounded-full">
                  All assigned ✓
                </span>
              )}
            </div>
            {/* Progress bar */}
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden w-full max-w-xs">
              <div
                className="h-full bg-green-500 rounded-full transition-all duration-500"
                style={{ width: units.length > 0 ? `${(assignedCount / units.length) * 100}%` : '0%' }}
              />
            </div>
            <p className="text-xs text-gray-400 mt-1">{assignedCount} of {units.length} assigned</p>
          </div>

          {/* Search */}
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Search unit…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="border border-gray-200 rounded-xl px-3 py-2 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />
            <button
              onClick={() => setShowImportModal(true)}
              className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-xl transition whitespace-nowrap"
            >
              Import CSV
            </button>
          </div>
        </div>

        {/* Bulk selection toolbar */}
        {selectedUnitIds.length > 0 && (
          <div className="bg-indigo-50 border-2 border-indigo-200 rounded-2xl px-5 py-4">
            <p className="text-sm font-bold text-indigo-800 mb-3">
              {selectedUnitIds.length} unit{selectedUnitIds.length > 1 ? 's' : ''} selected
            </p>
            <div className="flex items-center gap-2 flex-wrap">
              <select
                value={bulkAssignType}
                onChange={(e) => setBulkAssignType(e.target.value)}
                className="border border-indigo-300 px-3 py-2 text-sm rounded-xl bg-white min-w-[160px]"
              >
                <option value="">Keep current type</option>
                {unitTypes.map((ut) => (
                  <option key={ut.unit_type_id} value={ut.unit_type_id}>{ut.code} — {ut.name}</option>
                ))}
              </select>
              <select
                value={bulkVariant}
                onChange={(e) => setBulkVariant(e.target.value as UnitVariant)}
                className="border border-indigo-300 px-3 py-2 text-sm rounded-xl bg-white"
              >
                {Object.values(UnitVariant).map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
              <button
                onClick={() => handleBulkUpdate().catch(console.error)}
                disabled={updateWorking}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-xl disabled:opacity-50 transition"
              >
                {updateWorking ? 'Saving…' : 'Apply to Selected'}
              </button>
              <button
                onClick={() => setSelectedUnitIds([])}
                className="px-4 py-2 border border-indigo-300 text-indigo-600 text-sm rounded-xl hover:bg-white transition"
              >
                Clear
              </button>
            </div>
          </div>
        )}

        {/* ── UNASSIGNED UNITS — shown at top, prominent ── */}
        {filteredUntyped.length > 0 && (
          <div className="bg-amber-50 rounded-2xl border-2 border-amber-300 overflow-hidden">
            <div
              className="px-5 py-4 flex items-center justify-between cursor-pointer hover:bg-amber-100 transition"
              onClick={() => toggleExpanded('__untyped__')}
            >
              <div className="flex items-center gap-3">
                <span className="w-8 h-8 rounded-full bg-amber-400 text-white text-sm font-black flex items-center justify-center shrink-0">
                  !
                </span>
                <div>
                  <h3 className="font-bold text-amber-900 text-base">
                    {filteredUntyped.length} Unassigned Unit{filteredUntyped.length !== 1 ? 's' : ''}
                  </h3>
                  <p className="text-xs text-amber-700">These need a stone type before you can generate the PDF</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedUnitIds(filteredUntyped.map((u) => u.unit_id));
                  }}
                  className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-lg transition"
                >
                  Select All
                </button>
                <span className="text-amber-500 text-sm">{expandedTypeIds.has('__untyped__') ? '▲' : '▼'}</span>
              </div>
            </div>

            {expandedTypeIds.has('__untyped__') && (
              <div className="border-t border-amber-200 px-5 py-4">
                <div className="flex flex-wrap gap-2">
                  {filteredUntyped.map((u) => {
                    const sel = selectedUnitIds.includes(u.unit_id);
                    const isOpen = quickAssignUnitId === u.unit_id;
                    return (
                      <div key={u.unit_id} className="relative">
                        <button
                          onClick={() => setQuickAssignUnitId(isOpen ? null : u.unit_id)}
                          className={`
                            px-4 py-2 text-sm font-bold rounded-xl border-2 transition min-h-[40px]
                            ${sel
                              ? 'bg-indigo-600 border-indigo-600 text-white'
                              : 'bg-white border-amber-300 text-amber-800 hover:border-amber-500 hover:bg-amber-50'
                            }
                          `}
                        >
                          {u.code}
                          <span className="ml-1 text-xs opacity-60">▾</span>
                        </button>
                        {/* Quick-assign dropdown */}
                        {isOpen && (
                          <div className="absolute z-20 top-full left-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-lg min-w-[180px] py-1">
                            <p className="px-3 py-1.5 text-xs text-gray-400 font-bold border-b border-gray-100">Assign type</p>
                            {unitTypes.map((ut) => (
                              <button
                                key={ut.unit_type_id}
                                onClick={() => handleQuickAssign(u.unit_id, ut.unit_type_id)}
                                className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition font-medium"
                              >
                                {ut.code} — {ut.name}
                              </button>
                            ))}
                            {unitTypes.length === 0 && (
                              <p className="px-3 py-2 text-sm text-gray-400">No types yet — add one →</p>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Typed unit groups ── */}
        {unitTypes.length === 0 && units.length > 0 && (
          <div className="bg-white rounded-2xl border border-dashed border-gray-300 p-6 text-center text-sm text-gray-500">
            No unit types defined yet. Add a type in the panel on the right.
          </div>
        )}

        {unitTypes.map((ut) => {
          const typeUnits = filteredUnits(ut.unit_type_id);
          const expanded  = expandedTypeIds.has(ut.unit_type_id);
          const total     = units.filter((u) => u.unit_type_id === ut.unit_type_id).length;
          const allSel    = typeUnits.length > 0 && typeUnits.every((u) => selectedUnitIds.includes(u.unit_id));

          return (
            <div key={ut.unit_type_id} className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
              {/* Type header — always visible, large touch target */}
              <div
                className="px-5 py-4 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition"
                onClick={() => toggleExpanded(ut.unit_type_id)}
              >
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={allSel}
                    onChange={() => toggleTypeUnits(ut.unit_type_id)}
                    onClick={(e) => e.stopPropagation()}
                    className="w-4 h-4 rounded border-gray-300 text-indigo-600"
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-black text-gray-900 text-lg leading-none">{ut.code}</span>
                      {ut.is_mirror && (
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-bold rounded-full">MIR</span>
                      )}
                      {ut.is_ada && (
                        <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs font-bold rounded-full">ADA</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5">{ut.name}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-bold text-gray-700 bg-gray-100 px-3 py-1 rounded-full">
                    {total} units
                  </span>
                  <span className="text-gray-400">{expanded ? '▲' : '▼'}</span>
                </div>
              </div>

              {/* Unit chips — expanded — bigger touch targets */}
              {expanded && (
                <div className="border-t border-gray-100 px-5 py-4">
                  {typeUnits.length === 0 ? (
                    <p className="text-sm text-gray-400">
                      {search ? 'No units match your search.' : 'No units assigned to this type.'}
                    </p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {typeUnits.map((u) => {
                        const sel = selectedUnitIds.includes(u.unit_id);
                        return (
                          <button
                            key={u.unit_id}
                            type="button"
                            onClick={() => toggleUnit(u.unit_id)}
                            className={`
                              px-4 py-2 text-sm font-bold rounded-xl border-2 transition min-h-[40px]
                              ${sel
                                ? 'bg-indigo-600 border-indigo-600 text-white'
                                : u.status === 'archived'
                                  ? 'bg-gray-100 border-gray-200 text-gray-400'
                                  : 'bg-gray-50 border-gray-200 text-gray-700 hover:border-indigo-300 hover:bg-indigo-50'
                              }
                            `}
                          >
                            {u.code}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ══ RIGHT: tools sidebar ══════════════════════════════════════════ */}
      <div className="w-64 shrink-0 space-y-4 hidden lg:block">

        {/* Add Unit Type */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Add Stone Type</p>
          <div className="space-y-2">
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">Type Code</label>
              <input
                type="text"
                placeholder="e.g. 1A, 2B-MIR, ADA"
                value={newTypeCode}
                onChange={(e) => setNewTypeCode(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddType()}
                className="border border-gray-200 rounded-xl px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-300"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">Description</label>
              <input
                type="text"
                placeholder="e.g. 1 Bed Kitchen"
                value={newTypeName}
                onChange={(e) => setNewTypeName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddType()}
                className="border border-gray-200 rounded-xl px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-300"
              />
            </div>
            <button
              onClick={handleAddType}
              disabled={addTypeWorking || !newTypeCode.trim()}
              className="w-full py-2 bg-gray-900 hover:bg-gray-700 text-white text-sm font-bold rounded-xl disabled:opacity-40 transition"
            >
              {addTypeWorking ? 'Adding…' : '+ Add Type'}
            </button>
          </div>
          {/* Tip for MIR/ADA auto-detection */}
          <p className="text-xs text-gray-400 mt-2 leading-snug">
            Tip: include "MIR" or "ADA" in the code to auto-tag variants.
          </p>
        </div>

        {/* Existing types list */}
        {unitTypes.length > 0 && (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4">
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
              Types ({unitTypes.length})
            </p>
            <div className="space-y-2">
              {unitTypes.map((ut) => {
                const count = units.filter((u) => u.unit_type_id === ut.unit_type_id).length;
                return (
                  <div key={ut.unit_type_id} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="font-bold text-gray-800 truncate">{ut.code}</span>
                      {ut.is_mirror && <span className="text-blue-500 text-xs font-bold">MIR</span>}
                      {ut.is_ada    && <span className="text-emerald-600 text-xs font-bold">ADA</span>}
                    </div>
                    <span className="text-gray-400 text-xs font-medium shrink-0 ml-1">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Bulk generate */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Generate Units</p>
          <div className="space-y-2">
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">Prefix</label>
              <input type="text" placeholder="A-" value={bulkPrefix}
                onChange={(e) => setBulkPrefix(e.target.value)}
                className="border border-gray-200 rounded-xl px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-300"
              />
            </div>
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="text-xs font-semibold text-gray-600 block mb-1">From</label>
                <input type="number" placeholder="101" value={bulkStart}
                  onChange={(e) => setBulkStart(e.target.value)}
                  className="border border-gray-200 rounded-xl px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-300"
                />
              </div>
              <div className="flex-1">
                <label className="text-xs font-semibold text-gray-600 block mb-1">To</label>
                <input type="number" placeholder="120" value={bulkEnd}
                  onChange={(e) => setBulkEnd(e.target.value)}
                  className="border border-gray-200 rounded-xl px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-300"
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">Stone Type</label>
              <select value={bulkType} onChange={(e) => setBulkType(e.target.value)}
                className="border border-gray-200 rounded-xl px-3 py-2 text-sm w-full bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300"
              >
                <option value="">Assign type later</option>
                {unitTypes.map((ut) => (
                  <option key={ut.unit_type_id} value={ut.unit_type_id}>{ut.code} — {ut.name}</option>
                ))}
              </select>
            </div>
            <button
              onClick={() => handleBulkGenerate().catch(console.error)}
              disabled={bulkWorking || !bulkStart || !bulkEnd}
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold rounded-xl disabled:opacity-40 transition"
            >
              {bulkWorking ? 'Generating…' : 'Generate Units'}
            </button>
          </div>
        </div>

        {/* Import */}
        <button
          onClick={() => setShowImportModal(true)}
          className="w-full py-3 border-2 border-dashed border-gray-300 text-gray-500 text-sm font-bold rounded-2xl hover:border-indigo-400 hover:text-indigo-600 hover:bg-indigo-50 transition"
        >
          ↑ Import from CSV / Excel
        </button>
      </div>

      {showImportModal && (
        <ImportModal
          projectId={project.project_id}
          onClose={() => { setShowImportModal(false); loadData(); }}
        />
      )}

      {/* Close quick-assign on outside click */}
      {quickAssignUnitId && (
        <div
          className="fixed inset-0 z-10"
          onClick={() => setQuickAssignUnitId(null)}
        />
      )}
    </div>
  );
};

// ── Sub-components ─────────────────────────────────────────────────────────

interface BulkGenerateCardProps {
  unitTypes: UnitType[];
  bulkPrefix: string; setBulkPrefix: (v: string) => void;
  bulkStart: string;  setBulkStart:  (v: string) => void;
  bulkEnd: string;    setBulkEnd:    (v: string) => void;
  bulkType: string;   setBulkType:   (v: string) => void;
  bulkWorking: boolean;
  onGenerate: () => void;
  onCancel: () => void;
}

const BulkGenerateCard: React.FC<BulkGenerateCardProps> = (p) => (
  <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
    <h4 className="font-bold text-gray-900 mb-4">Generate Unit Numbers</h4>
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div>
        <label className="text-xs font-semibold text-gray-600 block mb-1">Prefix</label>
        <input type="text" placeholder="A-" value={p.bulkPrefix}
          onChange={(e) => p.setBulkPrefix(e.target.value)}
          className="border border-gray-200 rounded-xl px-3 py-2 text-sm w-full"
        />
      </div>
      <div>
        <label className="text-xs font-semibold text-gray-600 block mb-1">From #</label>
        <input type="number" placeholder="101" value={p.bulkStart}
          onChange={(e) => p.setBulkStart(e.target.value)}
          className="border border-gray-200 rounded-xl px-3 py-2 text-sm w-full"
        />
      </div>
      <div>
        <label className="text-xs font-semibold text-gray-600 block mb-1">To #</label>
        <input type="number" placeholder="120" value={p.bulkEnd}
          onChange={(e) => p.setBulkEnd(e.target.value)}
          className="border border-gray-200 rounded-xl px-3 py-2 text-sm w-full"
        />
      </div>
      <div>
        <label className="text-xs font-semibold text-gray-600 block mb-1">Type</label>
        <select value={p.bulkType} onChange={(e) => p.setBulkType(e.target.value)}
          className="border border-gray-200 rounded-xl px-3 py-2 text-sm w-full bg-white"
        >
          <option value="">None</option>
          {p.unitTypes.map((ut) => (
            <option key={ut.unit_type_id} value={ut.unit_type_id}>{ut.code}</option>
          ))}
        </select>
      </div>
    </div>
    <div className="flex gap-3 mt-4">
      <button
        onClick={p.onGenerate}
        disabled={p.bulkWorking || !p.bulkStart || !p.bulkEnd}
        className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold rounded-xl disabled:opacity-40 transition"
      >
        {p.bulkWorking ? 'Generating…' : 'Generate Units'}
      </button>
      <button onClick={p.onCancel}
        className="px-5 py-2 border border-gray-200 text-gray-600 text-sm rounded-xl hover:bg-gray-50 transition"
      >
        Cancel
      </button>
    </div>
  </div>
);
