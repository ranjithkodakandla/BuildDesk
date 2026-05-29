import React, { useEffect, useState } from 'react';
import { Project, UnitType, Unit, UnitVariant } from '../types/hierarchy';
import { projectsApi } from '../api/projects';

interface Props {
  project: Project;
}

export const HierarchyPanel: React.FC<Props> = ({ project }) => {
  const [unitTypes, setUnitTypes] = useState<UnitType[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [loading, setLoading] = useState(true);

  const [newTypeCode, setNewTypeCode] = useState('');
  const [newTypeName, setNewTypeName] = useState('');

  const [newUnitCode, setNewUnitCode] = useState('');
  const [selectedUnitType, setSelectedUnitType] = useState<string>('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [ut, u] = await Promise.all([
        projectsApi.listUnitTypes(project.project_id),
        projectsApi.listUnits(project.project_id)
      ]);
      setUnitTypes(ut);
      setUnits(u);
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
        <h2 className="text-lg font-bold mb-4">Units</h2>
        
        <div className="mb-4 flex space-x-2">
          <input 
            type="text" 
            placeholder="Unit Code (e.g. 101)" 
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
          <button onClick={handleCreateUnit} className="bg-blue-600 text-white px-4 py-2 rounded font-medium">Add Unit</button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
          {units.map(u => {
            const ut = unitTypes.find(t => t.unit_type_id === u.unit_type_id);
            return (
              <div key={u.unit_id} className="p-3 border rounded text-center bg-gray-50">
                <div className="font-bold text-gray-900">{u.code}</div>
                <div className="text-xs text-gray-500 mt-1">{ut ? ut.code : 'Untyped'}</div>
              </div>
            )
          })}
        </div>
      </section>
    </div>
  );
};
