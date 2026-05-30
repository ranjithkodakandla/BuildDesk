import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Project, UnitType, UnitVariant } from '../types/hierarchy';
import { Assembly, AssemblyType } from '../types/fabrication';
import { assembliesApi } from '../api/assemblies';
import { projectsApi } from '../api/projects';
import { AssemblyEditor } from './AssemblyEditor';

interface Props {
  project: Project;
}

export const AssembliesPanel: React.FC<Props> = ({ project }) => {
  const [assemblies, setAssemblies] = useState<Assembly[]>([]);
  const [unitTypes, setUnitTypes] = useState<UnitType[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  // Preview state for selected assembly
  const [svgUrl, setSvgUrl] = useState<string | null>(null);
  const [svgLoading, setSvgLoading] = useState(false);
  const svgBlobRef = useRef<string | null>(null);

  const [isCreating, setIsCreating] = useState(false);
  const [newAsmName, setNewAsmName] = useState('');
  const [newAsmType, setNewAsmType] = useState<AssemblyType>(AssemblyType.KITCHEN);
  const [newAsmUnitTypeId, setNewAsmUnitTypeId] = useState<string>('');
  const [creating, setCreating] = useState(false);

  const selected = assemblies.find((a) => a.assembly_id === selectedId) || null;

  const revokePreview = useCallback(() => {
    if (svgBlobRef.current) {
      URL.revokeObjectURL(svgBlobRef.current);
      svgBlobRef.current = null;
    }
  }, []);

  const loadPreview = useCallback(async (assemblyId: string, hasParts: boolean) => {
    if (!hasParts) {
      revokePreview();
      setSvgUrl(null);
      return;
    }
    setSvgLoading(true);
    try {
      revokePreview();
      const url = await assembliesApi.fetchSvgPreviewBlobUrl(assemblyId);
      svgBlobRef.current = url;
      setSvgUrl(url);
    } catch {
      setSvgUrl(null);
    } finally {
      setSvgLoading(false);
    }
  }, [revokePreview]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [asmList, utList] = await Promise.all([
        assembliesApi.listAssemblies(project.project_id),
        projectsApi.listUnitTypes(project.project_id),
      ]);
      setAssemblies(asmList);
      setUnitTypes(utList);
      if (!selectedId && asmList.length > 0) {
        setSelectedId(asmList[0].assembly_id || null);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [project.project_id]);

  // Load preview when selection changes
  useEffect(() => {
    if (!selectedId) { revokePreview(); setSvgUrl(null); return; }
    const asm = assemblies.find((a) => a.assembly_id === selectedId);
    if (!asm) return;
    loadPreview(selectedId, (asm.parts?.length ?? 0) > 0);
    return () => { /* cleanup happens on next call */ };
  }, [selectedId, assemblies]);

  useEffect(() => () => revokePreview(), [revokePreview]);

  const handleCreate = async () => {
    if (!newAsmName.trim()) return;
    setCreating(true);
    try {
      const created = await assembliesApi.createAssembly({
        project_id: project.project_id,
        unit_type_id: newAsmUnitTypeId || undefined,
        name: newAsmName.trim(),
        assembly_type: newAsmType,
        variant: UnitVariant.STANDARD,
        parts: [],
        notes: [],
      });
      setAssemblies((prev) => [...prev, created]);
      setIsCreating(false);
      setNewAsmName('');
      setSelectedId(created.assembly_id || null);
    } catch (e) {
      console.error(e);
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex gap-4 animate-pulse">
        <div className="w-64 h-96 bg-gray-100 rounded-xl" />
        <div className="flex-1 h-96 bg-gray-100 rounded-xl" />
      </div>
    );
  }

  if (editing && selected) {
    return (
      <AssemblyEditor
        assembly={selected}
        onBack={() => { setEditing(false); loadData(); }}
        onSaved={loadData}
      />
    );
  }

  const partCount = selected?.parts?.length ?? 0;
  const edgeCount = selected?.parts?.reduce((n, p) => n + (p.edges?.length || 0), 0) ?? 0;
  const cutoutCount = selected?.parts?.reduce((n, p) => n + (p.cutouts?.length || 0), 0) ?? 0;
  const totalSqft = selected?.parts?.reduce((n, p) => n + (p.dimensions.length * p.dimensions.depth / 144), 0) ?? 0;

  return (
    <div className="flex flex-col gap-4 max-w-6xl">
      {/* Header bar */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm px-5 py-3 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-gray-900">Shop Drawings</h2>
          <p className="text-xs text-gray-400">{assemblies.length} assembl{assemblies.length !== 1 ? 'ies' : 'y'} · fabrication part definitions</p>
        </div>
        <button
          onClick={() => setIsCreating(!isCreating)}
          className={`px-4 py-1.5 text-sm font-medium rounded-lg transition ${
            isCreating
              ? 'bg-gray-100 text-gray-700 border border-gray-300'
              : 'bg-indigo-600 hover:bg-indigo-700 text-white'
          }`}
        >
          {isCreating ? 'Cancel' : '+ New Assembly'}
        </button>
      </div>

      {/* Create form */}
      {isCreating && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs font-bold text-indigo-700 mb-1">Assembly Name</label>
            <input
              type="text"
              value={newAsmName}
              onChange={(e) => setNewAsmName(e.target.value)}
              placeholder="Kitchen A"
              className="border border-indigo-300 p-2 rounded-lg text-sm w-44 bg-white"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-indigo-700 mb-1">Type</label>
            <select
              value={newAsmType}
              onChange={(e) => setNewAsmType(e.target.value as AssemblyType)}
              className="border border-indigo-300 p-2 rounded-lg text-sm bg-white"
            >
              {Object.values(AssemblyType).map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-bold text-indigo-700 mb-1">Unit Type (optional)</label>
            <select
              value={newAsmUnitTypeId}
              onChange={(e) => setNewAsmUnitTypeId(e.target.value)}
              className="border border-indigo-300 p-2 rounded-lg text-sm bg-white w-44"
            >
              <option value="">— Any type —</option>
              {unitTypes.map((ut) => (
                <option key={ut.unit_type_id} value={ut.unit_type_id}>{ut.name || ut.code}</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleCreate}
            disabled={creating || !newAsmName.trim()}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition"
          >
            {creating ? 'Creating…' : 'Create Assembly'}
          </button>
        </div>
      )}

      {/* Main split layout */}
      <div className="flex gap-4 min-h-0" style={{ height: 'calc(100vh - 280px)', minHeight: 480 }}>

        {/* Assembly list */}
        <aside className="w-64 shrink-0 bg-white border border-gray-200 rounded-xl overflow-y-auto">
          <p className="text-xs font-bold text-gray-400 uppercase px-4 py-2.5 border-b border-gray-100 tracking-wider sticky top-0 bg-white">
            Assemblies
          </p>
          {assemblies.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-sm text-gray-400 mb-2">No assemblies yet.</p>
              <p className="text-xs text-gray-300">Create an assembly to define shop drawings.</p>
            </div>
          ) : (
            assemblies.map((asm) => {
              const ut = unitTypes.find((t) => t.unit_type_id === asm.unit_type_id);
              const parts = asm.parts?.length ?? 0;
              return (
                <button
                  key={asm.assembly_id}
                  type="button"
                  onClick={() => setSelectedId(asm.assembly_id || null)}
                  className={`w-full text-left px-4 py-3 border-b border-gray-50 transition ${
                    selectedId === asm.assembly_id
                      ? 'bg-indigo-50 border-l-2 border-l-indigo-500'
                      : 'hover:bg-gray-50 border-l-2 border-l-transparent'
                  }`}
                >
                  <p className={`text-sm font-semibold leading-tight ${selectedId === asm.assembly_id ? 'text-indigo-800' : 'text-gray-800'}`}>
                    {asm.name}
                  </p>
                  <div className="flex items-center gap-1.5 mt-1">
                    <span className="text-xs text-gray-400 capitalize">{asm.assembly_type.replace(/_/g, ' ')}</span>
                    {ut && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-medium">{ut.code}</span>
                    )}
                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${parts === 0 ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'}`}>
                      {parts} part{parts !== 1 ? 's' : ''}
                    </span>
                  </div>
                </button>
              );
            })
          )}
        </aside>

        {/* Detail pane */}
        <section className="flex-1 bg-white border border-gray-200 rounded-xl flex flex-col overflow-hidden">
          {!selected ? (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              <div className="text-center">
                <p className="text-lg font-medium mb-1">Select an assembly</p>
                <p className="text-sm">Choose from the list to view drawing details</p>
              </div>
            </div>
          ) : (
            <>
              {/* Assembly header */}
              <div className="border-b border-gray-100 px-6 py-4 flex items-start justify-between">
                <div>
                  <h3 className="text-xl font-bold text-gray-900">{selected.name}</h3>
                  <p className="text-sm text-gray-500 capitalize mt-0.5">
                    {selected.assembly_type.replace(/_/g, ' ')}
                    {(() => {
                      const ut = unitTypes.find((t) => t.unit_type_id === selected.unit_type_id);
                      return ut ? ` · Type ${ut.code}` : '';
                    })()}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={async () => {
                      if (!selected.assembly_id) return;
                      const dup = await assembliesApi.duplicateAssembly(selected.assembly_id, {
                        new_name: `${selected.name} (Copy)`,
                      });
                      setAssemblies((prev) => [...prev, dup]);
                    }}
                    className="px-3 py-1.5 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition"
                  >
                    Duplicate
                  </button>
                  <button
                    onClick={() => setEditing(true)}
                    className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-lg transition"
                  >
                    Edit Drawing
                  </button>
                </div>
              </div>

              {/* Drawing preview */}
              <div className="flex-1 bg-slate-50 flex items-center justify-center p-6 relative overflow-hidden">
                {svgLoading ? (
                  <div className="text-center">
                    <div className="w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    <p className="text-sm text-gray-400">Loading drawing…</p>
                  </div>
                ) : svgUrl ? (
                  <div className="w-full h-full flex items-center justify-center">
                    <img
                      src={svgUrl}
                      alt={`${selected.name} fabrication drawing`}
                      className="max-w-full max-h-full object-contain drop-shadow-sm"
                    />
                  </div>
                ) : (
                  <div className="text-center">
                    <div className="w-16 h-16 rounded-xl bg-slate-200 flex items-center justify-center mx-auto mb-3">
                      <span className="text-2xl text-slate-400">⬜</span>
                    </div>
                    <p className="text-gray-500 font-medium mb-1">
                      {partCount === 0 ? 'No parts defined' : 'Drawing not available'}
                    </p>
                    <p className="text-xs text-gray-400">
                      {partCount === 0
                        ? 'Open Edit Drawing to add parts and generate the shop drawing.'
                        : 'Edit the assembly to regenerate the preview.'}
                    </p>
                    <button
                      onClick={() => setEditing(true)}
                      className="mt-3 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg"
                    >
                      {partCount === 0 ? 'Add Parts' : 'Edit Drawing'}
                    </button>
                  </div>
                )}
              </div>

              {/* Stats strip */}
              <div className="border-t border-gray-100 px-6 py-3 grid grid-cols-4 gap-4 text-center bg-gray-50">
                {[
                  { label: 'Parts', value: String(partCount) },
                  { label: 'Edges', value: String(edgeCount) },
                  { label: 'Cutouts', value: String(cutoutCount) },
                  { label: 'Sq Ft', value: totalSqft > 0 ? totalSqft.toFixed(1) : '—' },
                ].map((s) => (
                  <div key={s.label}>
                    <p className="text-lg font-bold text-gray-900">{s.value}</p>
                    <p className="text-xs text-gray-500">{s.label}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
};
