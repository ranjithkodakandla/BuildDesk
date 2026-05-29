import React, { useState, useEffect } from 'react';
import { Assembly, Part, PartType, Position, EdgeType } from '../types/fabrication';
import { assembliesApi } from '../api/assemblies';

interface Props {
  assembly: Assembly;
  onBack: () => void;
  onSaved: () => void;
}

export const AssemblyEditor: React.FC<Props> = ({ assembly: initialAsm, onBack, onSaved }) => {
  const [asm, setAsm] = useState<Assembly>(initialAsm);
  const [loading, setLoading] = useState(false);
  const [svgUrl, setSvgUrl] = useState('');

  // Fetch full assembly details to ensure we have all nested data
  useEffect(() => {
    const fetchFull = async () => {
      if (initialAsm.assembly_id) {
        const full = await assembliesApi.getAssembly(initialAsm.assembly_id);
        setAsm(full);
        setSvgUrl(assembliesApi.getSvgPreviewUrl(initialAsm.assembly_id));
      }
    };
    fetchFull();
  }, [initialAsm.assembly_id]);

  const handleSave = async () => {
    if (!asm.assembly_id) return;
    setLoading(true);
    try {
      const updated = await assembliesApi.updateAssembly(asm.assembly_id, {
        project_id: asm.project_id,
        unit_id: asm.unit_id,
        unit_type_id: asm.unit_type_id,
        name: asm.name,
        assembly_type: asm.assembly_type,
        variant: asm.variant,
        parts: asm.parts,
        notes: asm.notes,
      });
      setAsm(updated);
      setSvgUrl(`${assembliesApi.getSvgPreviewUrl(asm.assembly_id)}?t=${Date.now()}`);
      onSaved();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const addPart = () => {
    setAsm({
      ...asm,
      parts: [
        ...asm.parts,
        {
          part_type: PartType.MAIN_TOP,
          name: `Part ${String.fromCharCode(65 + asm.parts.length)}`,
          dimensions: { length: 60, depth: 25.5 },
          edges: [],
          cutouts: [],
          holes: [],
          splashes: []
        }
      ]
    });
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col h-[calc(100vh-140px)]">
      <div className="border-b px-6 py-4 flex justify-between items-center bg-gray-50">
        <div className="flex items-center space-x-4">
          <button onClick={onBack} className="text-gray-500 hover:text-gray-900 font-medium">← Back</button>
          <h2 className="text-lg font-bold">Edit Assembly: {asm.name}</h2>
          <span className="bg-blue-100 text-blue-800 px-2 py-1 text-xs rounded uppercase font-bold">{asm.assembly_type}</span>
        </div>
        <button onClick={handleSave} disabled={loading} className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded font-bold shadow-sm disabled:opacity-50">
          {loading ? 'Saving...' : 'Save Assembly'}
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left pane: Data Editor */}
        <div className="w-1/2 overflow-y-auto border-r p-6 space-y-6 bg-gray-50">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-gray-900 text-lg">Parts Configuration</h3>
            <button onClick={addPart} className="text-sm bg-blue-100 text-blue-700 hover:bg-blue-200 px-3 py-1 rounded font-medium">+ Add Part</button>
          </div>

          {asm.parts.length === 0 ? (
            <p className="text-gray-500 text-sm">No parts defined. Add a part to begin.</p>
          ) : (
            asm.parts.map((part, idx) => (
              <PartEditor 
                key={idx} 
                part={part} 
                partIndex={idx}
                onChange={(newPart) => {
                  const newParts = [...asm.parts];
                  newParts[idx] = newPart;
                  setAsm({ ...asm, parts: newParts });
                }}
                onRemove={() => {
                  const newParts = [...asm.parts];
                  newParts.splice(idx, 1);
                  setAsm({ ...asm, parts: newParts });
                }}
              />
            ))
          )}
        </div>

        {/* Right pane: Live SVG Preview */}
        <div className="w-1/2 bg-[#eef2f7] flex items-center justify-center p-6 overflow-hidden">
          {svgUrl ? (
            <div className="bg-white shadow-lg border w-full h-full flex flex-col">
              <div className="bg-gray-800 text-white px-3 py-2 text-xs font-mono font-bold flex justify-between">
                <span>Fabrication Drawing Preview</span>
                <span className="text-gray-400">Phase 4 Engine</span>
              </div>
              <div className="flex-1 overflow-auto flex items-center justify-center p-4">
                <img src={svgUrl} alt="Assembly Preview" className="max-w-full max-h-full object-contain" />
              </div>
            </div>
          ) : (
            <div className="text-gray-400 font-medium">Save assembly to generate preview</div>
          )}
        </div>
      </div>
    </div>
  );
};

// --- Part Editor Component ---
const PartEditor = ({ part, partIndex, onChange, onRemove }: { part: Part, partIndex: number, onChange: (p: Part) => void, onRemove: () => void }) => {
  const updateDim = (field: 'length' | 'depth', val: number) => {
    onChange({ ...part, dimensions: { ...part.dimensions, [field]: val }});
  };

  const addEdge = () => {
    onChange({
      ...part,
      edges: [...part.edges, { position: Position.FRONT, edge_type: EdgeType.EASED }]
    });
  };

  const updateEdge = (idx: number, field: string, val: any) => {
    const newEdges = [...part.edges];
    newEdges[idx] = { ...newEdges[idx], [field]: val };
    onChange({ ...part, edges: newEdges });
  };

  const removeEdge = (idx: number) => {
    const newEdges = [...part.edges];
    newEdges.splice(idx, 1);
    onChange({ ...part, edges: newEdges });
  };

  return (
    <div className="bg-white p-4 rounded border shadow-sm">
      <div className="flex justify-between items-center mb-3">
        <h4 className="font-bold text-md text-gray-800">Part {String.fromCharCode(65 + partIndex)}</h4>
        <button onClick={onRemove} className="text-red-500 hover:text-red-700 text-sm font-medium">Remove</button>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-xs font-bold text-gray-700 mb-1">Name</label>
          <input type="text" value={part.name} onChange={e => onChange({...part, name: e.target.value})} className="w-full border p-1.5 text-sm rounded bg-gray-50" />
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-700 mb-1">Type</label>
          <select value={part.part_type} onChange={e => onChange({...part, part_type: e.target.value as PartType})} className="w-full border p-1.5 text-sm rounded bg-gray-50">
            {Object.values(PartType).map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-700 mb-1">Length (in)</label>
          <input type="number" step="0.1" value={part.dimensions.length} onChange={e => updateDim('length', parseFloat(e.target.value) || 0)} className="w-full border p-1.5 text-sm rounded bg-gray-50" />
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-700 mb-1">Depth (in)</label>
          <input type="number" step="0.1" value={part.dimensions.depth} onChange={e => updateDim('depth', parseFloat(e.target.value) || 0)} className="w-full border p-1.5 text-sm rounded bg-gray-50" />
        </div>
      </div>

      {/* Edges */}
      <div className="mb-4 bg-gray-50 p-3 rounded border">
        <div className="flex justify-between items-center mb-2">
          <h5 className="font-bold text-sm text-gray-700">Edges</h5>
          <button onClick={addEdge} className="text-xs text-blue-600 hover:underline">+ Add Edge</button>
        </div>
        {part.edges.map((e, i) => (
          <div key={i} className="flex space-x-2 mb-2 items-center">
            <select value={e.position} onChange={ev => updateEdge(i, 'position', ev.target.value)} className="flex-1 border p-1 text-xs rounded">
              {Object.values(Position).map(p => <option key={p} value={p}>{p.toUpperCase()}</option>)}
            </select>
            <select value={e.edge_type} onChange={ev => updateEdge(i, 'edge_type', ev.target.value)} className="flex-1 border p-1 text-xs rounded">
              {Object.values(EdgeType).map(t => <option key={t} value={t}>{t.toUpperCase()}</option>)}
            </select>
            <button onClick={() => removeEdge(i)} className="text-red-500 text-lg leading-none">×</button>
          </div>
        ))}
      </div>
      
      {/* Note: Cutouts, Holes, Splashes would follow similar UI patterns here. Keeping it concise for the artifact. */}
      <p className="text-xs text-gray-400 italic mt-2">Cutouts, Holes, and Splashes can be configured similarly.</p>
    </div>
  );
};
