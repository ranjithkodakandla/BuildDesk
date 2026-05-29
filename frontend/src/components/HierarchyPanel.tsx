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

  const [newTypeCode, setNewTypeCode] = useState('');
  const [newTypeName, setNewTypeName] = useState('');

  const [newUnitCode, setNewUnitCode] = useState('');
  const [selectedUnitType, setSelectedUnitType] = useState<string>('');
  const [selectedUnitIds, setSelectedUnitIds] = useState<string[]>([]);
  const [bulkPrefix, setBulkPrefix] = useState('');
  const [bulkStart, setBulkStart] = useState('');
  const [bulkEnd, setBulkEnd] = useState('');
  const [bulkType, setBulkType] = useState('');
  const [bulkAssignType, setBulkAssignType] = useState('');
  const [bulkVariant, setBulkVariant] = useState<UnitVariant>(UnitVariant.STANDARD);
  const [bulkStatus, setBulkStatus] = useState<UnitStatus>(UnitStatus.ACTIVE);

  const loadData = async () => {
    setLoading(true);
    try {
      const [ut, u] = await Promise.all([
        projectsApi.listUnitTypes(project.project_id),
        projectsApi.listUnits(project.project_id)
      ]);
      setUnitTypes(ut);
      setUnits(u);
      setSelectedUnitIds((selected) => selected.filter((id) => u.some((unit) => unit.unit_id === id)));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [project.project_id]);

  const handleCreateType = async () => {
    if (!newTypeCode) return;
    try {
      await projectsApi.createUnitType(project.project_id, {
        code: newTypeCode,
        name: newTypeName || newTypeCode,
        is_mirror: newTypeCode.includes('MIR'),
        is_ada: newTypeCode.includes('ADA'),
        sort_order: unitTypes.length + 1
      });
      setNewTypeCode('');
      setNewTypeName('');
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateUnit = async () => {
    if (!newUnitCode) return;
    try {
      await projectsApi.createUnit(project.project_id, {
        unit_type_id: selectedUnitType || undefined,
        name: `Unit ${newUnitCode}`,
        code: newUnitCode,
        variant: UnitVariant.STANDARD,
        sort_order: units.length + 1
      });
      setNewUnitCode('');
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  const toggleUnit = (unitId: string) => {
    setSelectedUnitIds((current) =>
      current.includes(unitId) ? current.filter((id) => id !== unitId) : [...current, unitId]
    );
  };

  const handleBulkGenerate = async () => {
    const start = parseInt(bulkStart, 10);
    const end = parseInt(bulkEnd, 10);
    if (!Number.isFinite(start) || !Number.isFinite(end) || start > end) return;
    await projectsApi.bulkCreateUnits(project.project_id, {
      start_number: start,
      end_number: end,
      prefix: bulkPrefix,
      unit_type_id: bulkType || undefined,
    });
    setBulkStart('');
    setBulkEnd('');
    loadData();
  };

  const handleBulkUpdate = async () => {
    if (selectedUnitIds.length === 0) return;
    await projectsApi.bulkUpdateUnits(project.project_id, {
      unit_ids: selectedUnitIds,
      unit_type_id: bulkAssignType || undefined,
      variant: bulkVariant,
      status: bulkStatus,
    });
    setSelectedUnitIds([]);
    loadData();
  };

  if (loading) return <div>Loading hierarchy...</div>;

  return (
    <div className="space-y-8">
      {/* Unit Types Section */}
      <section className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-lg font-bold mb-4">Unit Types</h2>
        
        <div className="mb-4 flex space-x-2">
          <input 
            type="text" 
            placeholder="Type Code (e.g. A1)" 
            value={newTypeCode} 
            onChange={(e) => setNewTypeCode(e.target.value)}
            className="border p-2 rounded flex-1"
          />
          <input 
            type="text" 
            placeholder="Name (e.g. 1 Bed / 1 Bath)" 
            value={newTypeName} 
            onChange={(e) => setNewTypeName(e.target.value)}
            className="border p-2 rounded flex-2"
          />
          <button onClick={handleCreateType} className="bg-blue-600 text-white px-4 py-2 rounded font-medium">Add Type</button>
        </div>

        <table className="min-w-full text-sm text-left text-gray-500 border">
          <thead className="text-xs text-gray-700 uppercase bg-gray-50 border-b">
            <tr>
              <th className="px-6 py-3">Code</th>
              <th className="px-6 py-3">Name</th>
              <th className="px-6 py-3">Variants</th>
              <th className="px-6 py-3">Unit Count</th>
            </tr>
          </thead>
          <tbody>
            {unitTypes.map(ut => {
              const count = units.filter(u => u.unit_type_id === ut.unit_type_id).length;
              return (
                <tr key={ut.unit_type_id} className="bg-white border-b">
                  <td className="px-6 py-4 font-bold text-gray-900">{ut.code}</td>
                  <td className="px-6 py-4">{ut.name}</td>
                  <td className="px-6 py-4 space-x-2">
                    {ut.is_mirror && <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">MIRROR</span>}
                    {ut.is_ada && <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">ADA</span>}
                    {!ut.is_mirror && !ut.is_ada && <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-6 py-4">{count}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </section>

      {/* Units Section */}
      <section className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Units</h2>
          <div className="flex items-center space-x-4">
            <div className="text-sm text-gray-500 font-medium">Total: {units.length}</div>
            <button
              onClick={() => setShowImportModal(true)}
              className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
            >
              Import CSV
            </button>
          </div>
        </div>
        
        {/* Bulk Create Form */}
        <div className="mb-6 p-4 bg-gray-50 border rounded-lg">
          <h3 className="text-sm font-bold mb-3 text-gray-700 uppercase">Bulk Generate Units</h3>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="block text-xs font-bold text-gray-500 mb-1">Prefix</label>
              <input type="text" placeholder="e.g. A-" value={bulkPrefix} onChange={(e) => setBulkPrefix(e.target.value)} className="border p-2 rounded w-20" />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-500 mb-1">Start #</label>
              <input type="number" placeholder="101" value={bulkStart} onChange={(e) => setBulkStart(e.target.value)} className="border p-2 rounded w-20" />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-500 mb-1">End #</label>
              <input type="number" placeholder="120" value={bulkEnd} onChange={(e) => setBulkEnd(e.target.value)} className="border p-2 rounded w-20" />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-500 mb-1">Type</label>
              <select value={bulkType} onChange={(e) => setBulkType(e.target.value)} className="border p-2 rounded w-40">
                <option value="">-- Type --</option>
                {unitTypes.map(ut => (
                  <option key={ut.unit_type_id} value={ut.unit_type_id}>{ut.code}</option>
                ))}
              </select>
            </div>
            <button 
              onClick={() => handleBulkGenerate().catch(console.error)}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded font-medium shadow-sm transition-colors"
            >
              Generate
            </button>
          </div>
        </div>

        <div className="mb-6 p-4 bg-blue-50 border border-blue-100 rounded-lg">
          <div className="flex flex-wrap items-end gap-3">
            <div className="text-sm font-bold text-blue-900 min-w-32">
              Selected: {selectedUnitIds.length}
            </div>
            <div>
              <label className="block text-xs font-bold text-blue-700 mb-1">Assign Type</label>
              <select value={bulkAssignType} onChange={(e) => setBulkAssignType(e.target.value)} className="border p-2 rounded w-44">
                <option value="">Keep type</option>
                {unitTypes.map(ut => (
                  <option key={ut.unit_type_id} value={ut.unit_type_id}>{ut.code}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-blue-700 mb-1">Variant</label>
              <select value={bulkVariant} onChange={(e) => setBulkVariant(e.target.value as UnitVariant)} className="border p-2 rounded w-32">
                {Object.values(UnitVariant).map((variant) => <option key={variant} value={variant}>{variant}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-blue-700 mb-1">Status</label>
              <select value={bulkStatus} onChange={(e) => setBulkStatus(e.target.value as UnitStatus)} className="border p-2 rounded w-32">
                <option value={UnitStatus.ACTIVE}>Active</option>
                <option value={UnitStatus.ARCHIVED}>Archived</option>
              </select>
            </div>
            <button
              onClick={() => handleBulkUpdate().catch(console.error)}
              disabled={selectedUnitIds.length === 0}
              className="bg-blue-600 disabled:bg-blue-300 text-white px-4 py-2 rounded font-medium"
            >
              Apply Bulk Update
            </button>
          </div>
        </div>

        <div className="mb-4 flex space-x-2">
          <input 
            type="text" 
            placeholder="Single Unit Code (e.g. 101)" 
            value={newUnitCode} 
            onChange={(e) => setNewUnitCode(e.target.value)}
            className="border p-2 rounded w-48"
          />
          <select 
            value={selectedUnitType} 
            onChange={(e) => setSelectedUnitType(e.target.value)}
            className="border p-2 rounded flex-1"
          >
            <option value="">-- Assign to Type --</option>
            {unitTypes.map(ut => (
              <option key={ut.unit_type_id} value={ut.unit_type_id}>{ut.code} - {ut.name}</option>
            ))}
          </select>
          <button onClick={handleCreateUnit} className="bg-blue-600 text-white px-4 py-2 rounded font-medium">Add Single Unit</button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2 max-h-96 overflow-y-auto p-1">
          {units.map(u => {
            const ut = unitTypes.find(t => t.unit_type_id === u.unit_type_id);
            return (
              <label key={u.unit_id} className={`p-3 border rounded text-center transition-colors ${selectedUnitIds.includes(u.unit_id) ? 'bg-blue-50 border-blue-300' : 'bg-gray-50 hover:bg-gray-100'}`}>
                <input type="checkbox" className="mb-2" checked={selectedUnitIds.includes(u.unit_id)} onChange={() => toggleUnit(u.unit_id)} />
                <div className="font-bold text-gray-900">{u.code}</div>
                <div className="text-xs text-gray-500 mt-1">{ut ? ut.code : 'Untyped'}</div>
                <div className="text-xs text-gray-400 mt-1">{u.status || 'active'}</div>
              </label>
            )
          })}
        </div>
      </section>

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
