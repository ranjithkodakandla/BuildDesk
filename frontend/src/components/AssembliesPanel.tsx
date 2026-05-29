import React, { useEffect, useState } from 'react';
import { Project, UnitType } from '../types/hierarchy';
import { Assembly, AssemblyType, UnitVariant } from '../types/fabrication';
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
  const [selectedAssembly, setSelectedAssembly] = useState<Assembly | null>(null);
  
  const [isCreating, setIsCreating] = useState(false);
  const [newAsmName, setNewAsmName] = useState('');
  const [newAsmType, setNewAsmType] = useState<AssemblyType>(AssemblyType.KITCHEN);
  const [newAsmUnitTypeId, setNewAsmUnitTypeId] = useState<string>('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [asmList, utList] = await Promise.all([
        assembliesApi.listAssemblies(project.project_id),
        projectsApi.listUnitTypes(project.project_id)
      ]);
      setAssemblies(asmList);
      setUnitTypes(utList);
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
        notes: []
      });
      setAssemblies([...assemblies, created]);
      setIsCreating(false);
      setNewAsmName('');
      setSelectedAssembly(created);
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <div>Loading assemblies...</div>;

  if (selectedAssembly) {
    return (
      <AssemblyEditor 
        assembly={selectedAssembly} 
        onBack={() => {
          setSelectedAssembly(null);
          loadData();
        }}
        onSaved={loadData}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm border border-gray-200">
        <div>
          <h2 className="text-lg font-bold">Project Assemblies</h2>
          <p className="text-sm text-gray-500">Manage fabrication assemblies like Kitchens, Vanities, Islands.</p>
        </div>
        <button 
          onClick={() => setIsCreating(!isCreating)}
          className="bg-blue-600 text-white px-4 py-2 rounded font-medium"
        >
          {isCreating ? 'Cancel' : '+ New Assembly'}
        </button>
      </div>

      {isCreating && (
        <div className="bg-blue-50 p-6 rounded-lg border border-blue-200 flex space-x-4 items-end">
          <div className="flex-1">
            <label className="block text-xs font-bold text-gray-700 mb-1">Assembly Name</label>
            <input type="text" value={newAsmName} onChange={e => setNewAsmName(e.target.value)} className="w-full border p-2 rounded" placeholder="e.g. Master Vanity" />
          </div>
          <div className="flex-1">
            <label className="block text-xs font-bold text-gray-700 mb-1">Type</label>
            <select value={newAsmType} onChange={e => setNewAsmType(e.target.value as AssemblyType)} className="w-full border p-2 rounded bg-white">
              {Object.values(AssemblyType).map(t => <option key={t} value={t}>{t.replace('_', ' ').toUpperCase()}</option>)}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-xs font-bold text-gray-700 mb-1">Assign to Unit Type</label>
            <select value={newAsmUnitTypeId} onChange={e => setNewAsmUnitTypeId(e.target.value)} className="w-full border p-2 rounded bg-white">
              <option value="">-- None --</option>
              {unitTypes.map(ut => <option key={ut.unit_type_id} value={ut.unit_type_id}>{ut.code} - {ut.name}</option>)}
            </select>
          </div>
          <button onClick={handleCreate} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded font-bold">Create</button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {assemblies.map(asm => {
          const ut = unitTypes.find(t => t.unit_type_id === asm.unit_type_id);
          return (
            <div key={asm.assembly_id} className="bg-white p-5 rounded-lg shadow-sm border border-gray-200 hover:border-blue-400 hover:shadow-md transition">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-bold text-lg text-gray-900">{asm.name}</h3>
                <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs font-bold uppercase">{asm.assembly_type.replace('_', ' ')}</span>
              </div>
              <p className="text-sm text-gray-600 mb-4">Assigned to: {ut ? <span className="font-bold">{ut.code}</span> : 'Unassigned'}</p>
              
              <div className="flex justify-between items-center text-sm text-gray-500 mb-6">
                <span>{asm.parts?.length || 0} Parts</span>
                <span>{asm.notes?.length || 0} Notes</span>
              </div>
              
              <div className="flex gap-2">
                <button 
                  onClick={() => setSelectedAssembly(asm)}
                  className="flex-1 border border-blue-600 text-blue-600 hover:bg-blue-50 py-2 rounded font-medium"
                >
                  Edit Assembly
                </button>
                <button 
                  onClick={async () => {
                    const confirmDup = window.confirm(`Duplicate "${asm.name}"?`);
                    if (confirmDup) {
                      try {
                        const duplicate = await assembliesApi.duplicateAssembly(asm.assembly_id, {
                          new_name: `${asm.name} (Copy)`
                        });
                        setAssemblies([...assemblies, duplicate]);
                      } catch(e) {
                        console.error(e);
                      }
                    }
                  }}
                  className="flex-1 border border-gray-300 text-gray-700 hover:bg-gray-50 py-2 rounded font-medium"
                >
                  Duplicate
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  );
};
