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
  const [showTools, setShowTools] = useState(false);

  // Selection state
  const [selectedUnitIds, setSelectedUnitIds] = useState<string[]>([]);
  const [expandedTypeIds, setExpandedTypeIds] = useState<Set<string>>(new Set());

  // Bulk generate form
  const [bulkPrefix, setBulkPrefix] = useState('');
  const [bulkStart, setBulkStart] = useState('');
  const [bulkEnd, setBulkEnd] = useState('');
  const [bulkType, setBulkType] = useState('');
  const [bulkWorking, setBulkWorking] = useState(false);

  // Bulk update
  const [bulkAssignType, setBulkAssignType] = useState('');
  const [bulkVariant, setBulkVariant] = useState<UnitVariant>(UnitVariant.STANDARD);
  const [bulkStatus, setBulkStatus] = useState<UnitStatus>(UnitStatus.ACTIVE);
  const [updateWorking, setUpdateWorking] = useState(false);

  // Add type form
  const [newTypeCode, setNewTypeCode] = useState('');
  const [newTypeName, setNewTypeName] = useState('');
  const [addTypeWorking, setAddTypeWorking] = useState(false);

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

  const toggleExpanded = (typeId: string) => {
    setExpandedTypeIds((prev) => {
      const next = new Set(prev);
      next.has(typeId) ? next.delete(typeId) : next.add(typeId);
      return next;
    });
  };

  const toggleUnit = (unitId: string) => {
    setSelectedUnitIds((cur) =>
      cur.includes(unitId) ? cur.filter((id) => id !== unitId) : [...cur, unitId]
    );
  };

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
    const end = parseInt(bulkEnd, 10);
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

  const untypedUnits = units.filter((u) => !u.unit_type_id);

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-14 bg-gray-100 rounded-xl" />
        <div className="h-32 bg-gray-100 rounded-xl" />
        <div className="h-32 bg-gray-100 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-5xl">

      {/* Summary bar */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm px-5 py-3 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-5 text-sm">
          <span className="font-bold text-gray-900">{units.length} Units</span>
          <span className="text-gray-400">·</span>
          <span className="text-gray-600">{unitTypes.length} Types</span>
          {untypedUnits.length > 0 && (
            <>
              <span className="text-gray-400">·</span>
              <span className="text-amber-600 font-medium">{untypedUnits.length} Unassigned</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowImportModal(true)}
            className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition"
          >
            Import CSV
          </button>
          <button
            onClick={() => setShowTools(!showTools)}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition ${
              showTools
                ? 'bg-indigo-50 border-indigo-200 text-indigo-700'
                : 'border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            Tools {showTools ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {/* Bulk selection toolbar — only when units are selected */}
      {selectedUnitIds.length > 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl px-5 py-3 flex items-center flex-wrap gap-3">
          <span className="text-sm font-bold text-indigo-800">{selectedUnitIds.length} selected</span>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={bulkAssignType}
              onChange={(e) => setBulkAssignType(e.target.value)}
              className="border border-indigo-300 p-1.5 text-sm rounded-lg bg-white"
            >
              <option value="">Keep type</option>
              {unitTypes.map((ut) => (
                <option key={ut.unit_type_id} value={ut.unit_type_id}>{ut.code} — {ut.name}</option>
              ))}
            </select>
            <select
              value={bulkVariant}
              onChange={(e) => setBulkVariant(e.target.value as UnitVariant)}
              className="border border-indigo-300 p-1.5 text-sm rounded-lg bg-white"
            >
              {Object.values(UnitVariant).map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
            <select
              value={bulkStatus}
              onChange={(e) => setBulkStatus(e.target.value as UnitStatus)}
              className="border border-indigo-300 p-1.5 text-sm rounded-lg bg-white"
            >
              <option value={UnitStatus.ACTIVE}>Active</option>
              <option value={UnitStatus.ARCHIVED}>Archived</option>
            </select>
            <button
              onClick={() => handleBulkUpdate().catch(console.error)}
              disabled={updateWorking}
              className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition"
            >
              {updateWorking ? 'Updating…' : 'Apply to Selected'}
            </button>
            <button
              onClick={() => setSelectedUnitIds([])}
              className="px-3 py-1.5 border border-indigo-300 text-indigo-600 text-sm rounded-lg hover:bg-white transition"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Tools panel — collapsed by default */}
      {showTools && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-5">

          {/* Add Unit Type */}
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">Add Unit Type</p>
            <div className="flex gap-2 items-end">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Code</label>
                <input
                  type="text"
                  placeholder="A1"
                  value={newTypeCode}
                  onChange={(e) => setNewTypeCode(e.target.value)}
                  className="border border-gray-300 p-2 rounded-lg text-sm w-24"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Name</label>
                <input
                  type="text"
                  placeholder="1 Bed / 1 Bath"
                  value={newTypeName}
                  onChange={(e) => setNewTypeName(e.target.value)}
                  className="border border-gray-300 p-2 rounded-lg text-sm w-48"
                />
              </div>
              <button
                onClick={handleAddType}
                disabled={addTypeWorking || !newTypeCode.trim()}
                className="px-4 py-2 bg-gray-800 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition"
              >
                {addTypeWorking ? 'Adding…' : 'Add Type'}
              </button>
            </div>
          </div>

          <div className="border-t border-gray-100" />

          {/* Bulk generate */}
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">Bulk Generate Units</p>
            <div className="flex gap-2 items-end flex-wrap">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Prefix</label>
                <input
                  type="text"
                  placeholder="A-"
                  value={bulkPrefix}
                  onChange={(e) => setBulkPrefix(e.target.value)}
                  className="border border-gray-300 p-2 rounded-lg text-sm w-20"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Start #</label>
                <input
                  type="number"
                  placeholder="101"
                  value={bulkStart}
                  onChange={(e) => setBulkStart(e.target.value)}
                  className="border border-gray-300 p-2 rounded-lg text-sm w-20"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">End #</label>
                <input
                  type="number"
                  placeholder="120"
                  value={bulkEnd}
                  onChange={(e) => setBulkEnd(e.target.value)}
                  className="border border-gray-300 p-2 rounded-lg text-sm w-20"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Type</label>
                <select
                  value={bulkType}
                  onChange={(e) => setBulkType(e.target.value)}
                  className="border border-gray-300 p-2 rounded-lg text-sm w-44 bg-white"
                >
                  <option value="">None</option>
                  {unitTypes.map((ut) => (
                    <option key={ut.unit_type_id} value={ut.unit_type_id}>{ut.code} — {ut.name}</option>
                  ))}
                </select>
              </div>
              <button
                onClick={() => handleBulkGenerate().catch(console.error)}
                disabled={bulkWorking || !bulkStart || !bulkEnd}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition"
              >
                {bulkWorking ? 'Generating…' : 'Generate'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Unit type cards — main content */}
      {unitTypes.length === 0 && units.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-400 mb-2 font-medium">No units yet</p>
          <p className="text-sm text-gray-400 mb-4">Import a unit schedule or use Tools to generate units.</p>
          <button
            onClick={() => setShowImportModal(true)}
            className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg"
          >
            Import CSV
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {unitTypes.map((ut) => {
            const typeUnits = units.filter((u) => u.unit_type_id === ut.unit_type_id);
            const expanded = expandedTypeIds.has(ut.unit_type_id);
            const allTypeSelected = typeUnits.length > 0 && typeUnits.every((u) => selectedUnitIds.includes(u.unit_id));

            return (
              <div key={ut.unit_type_id} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                {/* Type header */}
                <div
                  className="px-5 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition"
                  onClick={() => toggleExpanded(ut.unit_type_id)}
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={allTypeSelected}
                      onChange={() => toggleTypeUnits(ut.unit_type_id)}
                      onClick={(e) => e.stopPropagation()}
                      className="rounded border-gray-300"
                    />
                    <span className="font-bold text-gray-900 text-base">{ut.code}</span>
                    <span className="text-gray-500 text-sm">{ut.name}</span>
                    {ut.is_mirror && (
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-bold rounded-full">MIR</span>
                    )}
                    {ut.is_ada && (
                      <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-bold rounded-full">ADA</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-500 font-medium">{typeUnits.length} units</span>
                    <span className="text-gray-400 text-sm">{expanded ? '▲' : '▼'}</span>
                  </div>
                </div>

                {/* Unit chips — expanded */}
                {expanded && (
                  <div className="border-t border-gray-100 px-5 py-4">
                    {typeUnits.length === 0 ? (
                      <p className="text-sm text-gray-400">No units assigned to this type.</p>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {typeUnits.map((u) => {
                          const sel = selectedUnitIds.includes(u.unit_id);
                          return (
                            <button
                              key={u.unit_id}
                              type="button"
                              onClick={() => toggleUnit(u.unit_id)}
                              className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition ${
                                sel
                                  ? 'bg-indigo-600 border-indigo-600 text-white'
                                  : u.status === 'archived'
                                    ? 'bg-gray-100 border-gray-200 text-gray-400'
                                    : 'bg-gray-50 border-gray-200 text-gray-700 hover:border-indigo-300 hover:bg-indigo-50'
                              }`}
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

          {/* Untyped units */}
          {untypedUnits.length > 0 && (
            <div className="bg-white rounded-xl border border-amber-200 shadow-sm overflow-hidden">
              <div
                className="px-5 py-3 flex items-center justify-between cursor-pointer hover:bg-amber-50 transition"
                onClick={() => toggleExpanded('__untyped__')}
              >
                <div className="flex items-center gap-3">
                  <span className="font-bold text-amber-700">Unassigned</span>
                  <span className="text-amber-600 text-sm">No type — assign via bulk update</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-amber-600 font-medium">{untypedUnits.length} units</span>
                  <span className="text-amber-400 text-sm">{expandedTypeIds.has('__untyped__') ? '▲' : '▼'}</span>
                </div>
              </div>
              {expandedTypeIds.has('__untyped__') && (
                <div className="border-t border-amber-100 px-5 py-4">
                  <div className="flex flex-wrap gap-2">
                    {untypedUnits.map((u) => {
                      const sel = selectedUnitIds.includes(u.unit_id);
                      return (
                        <button
                          key={u.unit_id}
                          type="button"
                          onClick={() => toggleUnit(u.unit_id)}
                          className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition ${
                            sel
                              ? 'bg-indigo-600 border-indigo-600 text-white'
                              : 'bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100'
                          }`}
                        >
                          {u.code}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {showImportModal && (
        <ImportModal
          projectId={project.project_id}
          onClose={() => {
            setShowImportModal(false);
            loadData();
          }}
        />
      )}
    </div>
  );
};
