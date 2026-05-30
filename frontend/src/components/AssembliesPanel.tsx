import React, { useEffect, useState } from 'react';
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

  const [isCreating, setIsCreating] = useState(false);
  const [newAsmName, setNewAsmName] = useState('');
  const [newAsmType, setNewAsmType] = useState<AssemblyType>(AssemblyType.KITCHEN);
  const [newAsmUnitTypeId, setNewAsmUnitTypeId] = useState<string>('');

  const selected = assemblies.find((a) => a.assembly_id === selectedId) || null;

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

  useEffect(() => {
    loadData();
  }, [project.project_id]);

  const handleCreate = async () => {
    if (!newAsmName) return;
    try {
      const created = await assembliesApi.createAssembly({
        project_id: project.project_id,
        unit_type_id: newAsmUnitTypeId || undefined,
        name: newAsmName,
        assembly_type: newAsmType,
        variant: UnitVariant.STANDARD,
        parts: [],
        notes: [],
      });
      setAssemblies([...assemblies, created]);
      setIsCreating(false);
      setNewAsmName('');
      setSelectedId(created.assembly_id || null);
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <div>Loading fabrication…</div>;

  if (editing && selected) {
    return (
      <AssemblyEditor
        assembly={selected}
        onBack={() => {
          setEditing(false);
          loadData();
        }}
        onSaved={loadData}
      />
    );
  }

  return (
    <div className="flex flex-col h-full min-h-[560px] space-y-4">
      <div className="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm border border-gray-200">
        <div>
          <h2 className="text-lg font-bold">Fabrication</h2>
          <p className="text-sm text-gray-500">Assemblies and shop-ready part definitions</p>
        </div>
        <button
          onClick={() => setIsCreating(!isCreating)}
          className="bg-indigo-600 text-white px-4 py-2 rounded font-medium text-sm"
        >
          {isCreating ? 'Cancel' : '+ New Assembly'}
        </button>
      </div>

      {isCreating && (
        <div className="bg-indigo-50 p-4 rounded-lg border border-indigo-200 flex flex-wrap gap-3 items-end">
          <input
            type="text"
            value={newAsmName}
            onChange={(e) => setNewAsmName(e.target.value)}
            className="border p-2 rounded flex-1 min-w-[180px]"
            placeholder="Kitchen A"
          />
          <select
            value={newAsmUnitTypeId}
            onChange={(e) => setNewAsmUnitTypeId(e.target.value)}
            className="border p-2 rounded bg-white min-w-[140px]"
          >
            <option value="">Unit type (optional)</option>
            {unitTypes.map((ut) => (
              <option key={ut.unit_type_id} value={ut.unit_type_id}>
                {ut.name || ut.code}
              </option>
            ))}
          </select>
          <select
            value={newAsmType}
            onChange={(e) => setNewAsmType(e.target.value as AssemblyType)}
            className="border p-2 rounded bg-white"
          >
            {Object.values(AssemblyType).map((t) => (
              <option key={t} value={t}>
                {t.replace('_', ' ')}
              </option>
            ))}
          </select>
          <button onClick={handleCreate} className="bg-indigo-600 text-white px-4 py-2 rounded font-medium">
            Create
          </button>
        </div>
      )}

      <div className="flex flex-1 gap-4 min-h-0">
        <aside className="w-64 shrink-0 bg-white border border-gray-200 rounded-lg overflow-y-auto">
          <p className="text-xs font-bold text-gray-400 uppercase px-4 py-3 border-b">Assemblies</p>
          {assemblies.map((asm) => (
            <button
              key={asm.assembly_id}
              type="button"
              onClick={() => setSelectedId(asm.assembly_id || null)}
              className={`w-full text-left px-4 py-3 border-b border-gray-100 text-sm ${
                selectedId === asm.assembly_id ? 'bg-indigo-50 text-indigo-800 font-semibold' : 'hover:bg-gray-50'
              }`}
            >
              {asm.name}
            </button>
          ))}
          {assemblies.length === 0 && (
            <p className="p-4 text-sm text-gray-400">No assemblies yet</p>
          )}
        </aside>

        <section className="flex-1 bg-white border border-gray-200 rounded-lg p-5 flex flex-col">
          {!selected ? (
            <p className="text-gray-400 text-sm">Select an assembly</p>
          ) : (
            <>
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-bold text-gray-900">{selected.name}</h3>
                  <p className="text-sm text-gray-500 capitalize">{selected.assembly_type.replace('_', ' ')}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setEditing(true)}
                    className="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium"
                  >
                    Edit
                  </button>
                  <button
                    onClick={async () => {
                      if (!selected.assembly_id) return;
                      const duplicate = await assembliesApi.duplicateAssembly(selected.assembly_id, {
                        new_name: `${selected.name} (Copy)`,
                      });
                      setAssemblies([...assemblies, duplicate]);
                    }}
                    className="border border-gray-300 px-4 py-2 rounded text-sm"
                  >
                    Duplicate
                  </button>
                </div>
              </div>

              <div className="flex-1 bg-slate-50 border border-dashed border-slate-200 rounded-lg flex items-center justify-center min-h-[220px] mb-4">
                <p className="text-slate-400 text-sm">
                  {selected.parts?.length || 0} parts · Open Edit for live SVG preview
                </p>
              </div>

              <div className="grid grid-cols-3 gap-3 text-sm">
                <div className="bg-gray-50 p-3 rounded">
                  <p className="font-bold text-gray-700 mb-1">Parts</p>
                  <p className="text-gray-600">{selected.parts?.length || 0}</p>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <p className="font-bold text-gray-700 mb-1">Edges</p>
                  <p className="text-gray-600">
                    {selected.parts?.reduce((n, p) => n + (p.edges?.length || 0), 0) || 0}
                  </p>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <p className="font-bold text-gray-700 mb-1">Cutouts</p>
                  <p className="text-gray-600">
                    {selected.parts?.reduce((n, p) => n + (p.cutouts?.length || 0), 0) || 0}
                  </p>
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
};
