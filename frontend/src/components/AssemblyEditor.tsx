import React, { useState, useEffect, useRef } from 'react';
import {
  Assembly, Part, PartType, Position, EdgeType,
  CutoutType, MountType, Cutout, Hole, SplashType, Splash,
} from '../types/fabrication';
import { assembliesApi } from '../api/assemblies';

interface Props {
  assembly: Assembly;
  onBack: () => void;
  onSaved: () => void;
}

export const AssemblyEditor: React.FC<Props> = ({ assembly: initialAsm, onBack, onSaved }) => {
  const [asm, setAsm] = useState<Assembly>(initialAsm);
  const [loading, setLoading] = useState(false);
  const [previewError] = useState<string | null>(null);
  const [selectedPartIdx, setSelectedPartIdx] = useState<number | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const fetchFull = async () => {
      if (initialAsm.assembly_id) {
        try {
          const full = await assembliesApi.getAssembly(initialAsm.assembly_id);
          setAsm(full);
        } catch (e) {
          console.error(e);
        }
      }
    };
    fetchFull();
  }, [initialAsm.assembly_id]);

  // Live canvas preview — re-renders on every parts change (BUG A fix)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, W, H);

    const parts = asm.parts ?? [];
    if (parts.length === 0) {
      ctx.fillStyle = '#94a3b8';
      ctx.font = '12px Helvetica, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Add parts to see preview', W / 2, H / 2);
      return;
    }

    const PAD = 36;
    const totalW = parts.reduce((s, p) => s + p.dimensions.length, 0);
    const maxH   = Math.max(...parts.map(p => p.dimensions.depth));
    const scaleX = (W - PAD * 2) / Math.max(totalW, 0.001);
    const scaleY = (H - PAD * 2) / Math.max(maxH,   0.001);
    const scale  = Math.min(scaleX, scaleY) * 0.75;

    const drawW = totalW * scale;
    const drawH = maxH   * scale;
    const startX = (W - drawW) / 2;
    const startY = (H - drawH) / 2;

    const EDGE_CODES: Record<string, string> = {
      eased: 'X', bullnose: 'B', laminated_bullnose: 'LB',
      laminated_eased: 'LE', raw: 'RAW', seam: 'S',
    };

    let cx = startX;
    parts.forEach((part, idx) => {
      const pw = part.dimensions.length * scale;
      const ph = part.dimensions.depth  * scale;
      const py = startY + (drawH - ph) / 2;

      // White rect
      ctx.strokeStyle = '#1a2332';
      ctx.lineWidth = 1.5;
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(cx, py, pw, ph);
      ctx.strokeRect(cx, py, pw, ph);

      // Part label
      const label = String.fromCharCode(65 + idx);
      ctx.fillStyle = '#1a2332';
      ctx.font = `bold ${Math.min(16, ph * 0.4)}px Helvetica, sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText(label, cx + pw / 2, py + ph / 2 + 5);

      // Edge codes
      const edgeMap: Record<string, string> = {};
      (part.edges ?? []).forEach(e => { edgeMap[e.position] = e.edge_type; });
      const sides: [string, number, number][] = [
        ['front', cx + pw / 2, py + ph],
        ['back',  cx + pw / 2, py],
        ['left',  cx,          py + ph / 2],
        ['right', cx + pw,     py + ph / 2],
      ];
      sides.forEach(([pos, ex, ey]) => {
        const code = EDGE_CODES[edgeMap[pos] ?? 'eased'] ?? 'X';
        ctx.font = 'bold 7px Helvetica, sans-serif';
        ctx.textAlign = 'center';
        const tw = ctx.measureText(code).width + 4;
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(ex - tw / 2, ey - 6, tw, 10);
        ctx.fillStyle = '#000000';
        ctx.fillText(code, ex, ey + 2);
      });

      // Width dim below
      ctx.strokeStyle = '#333333';
      ctx.lineWidth = 0.5;
      ctx.setLineDash([]);
      const dimY = py + ph + 14;
      ctx.beginPath();
      ctx.moveTo(cx, py + ph); ctx.lineTo(cx, dimY);
      ctx.moveTo(cx + pw, py + ph); ctx.lineTo(cx + pw, dimY);
      ctx.moveTo(cx, dimY); ctx.lineTo(cx + pw, dimY);
      ctx.stroke();
      ctx.fillStyle = '#333333';
      ctx.font = '6px Helvetica, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`${part.dimensions.length}" × ${part.dimensions.depth}"`, cx + pw / 2, dimY + 9);

      cx += pw;
    });
  }, [asm.parts]);

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
      onSaved();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const addPart = () => {
    const idx = asm.parts.length;
    const newPart: Part = {
      part_type: PartType.MAIN_TOP,
      name: `Part ${String.fromCharCode(65 + idx)}`,
      dimensions: { length: 60, depth: 25.5 },
      edges: [],
      cutouts: [],
      holes: [],
      splashes: [],
    };
    setAsm({ ...asm, parts: [...asm.parts, newPart] });
    setSelectedPartIdx(idx);
  };

  const updatePart = (idx: number, updated: Part) => {
    const parts = [...asm.parts];
    parts[idx] = updated;
    setAsm({ ...asm, parts });
  };

  const removePart = (idx: number) => {
    const parts = [...asm.parts];
    parts.splice(idx, 1);
    setAsm({ ...asm, parts });
    setSelectedPartIdx(null);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col" style={{ height: 'calc(100vh - 140px)' }}>
      {/* Editor header */}
      <div className="border-b px-6 py-3 flex justify-between items-center bg-gray-50 rounded-t-xl">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-gray-500 hover:text-gray-900 text-sm font-medium">
            ← Back
          </button>
          <div>
            <h2 className="text-base font-bold text-gray-900">Editing: {asm.name}</h2>
            <p className="text-xs text-gray-400 capitalize">{asm.assembly_type.replace(/_/g, ' ')} · {asm.parts.length} part{asm.parts.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={loading}
          className="bg-green-600 hover:bg-green-700 text-white px-5 py-2 rounded-lg font-bold text-sm shadow-sm disabled:opacity-50 transition"
        >
          {loading ? 'Saving…' : 'Save Assembly'}
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left: parts list + selected part editor */}
        <div className="w-1/2 flex flex-col border-r overflow-hidden">
          {/* Parts list */}
          <div className="border-b bg-gray-50 px-4 py-2 flex items-center justify-between">
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wide">Parts</p>
            <button
              onClick={addPart}
              className="text-sm bg-indigo-100 text-indigo-700 hover:bg-indigo-200 px-3 py-1 rounded-lg font-medium"
            >
              + Add Part
            </button>
          </div>

          {asm.parts.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-center p-6">
              <div>
                <p className="text-gray-400 font-medium mb-2">No parts defined</p>
                <p className="text-xs text-gray-300 mb-3">Add a part to start defining the shop drawing.</p>
                <button
                  onClick={addPart}
                  className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg"
                >
                  Add First Part
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Part selector tabs */}
              <div className="flex gap-1 px-3 pt-2 border-b border-gray-100 bg-white overflow-x-auto">
                {asm.parts.map((p, i) => (
                  <button
                    key={i}
                    onClick={() => setSelectedPartIdx(i)}
                    className={`px-3 py-1.5 text-xs font-bold rounded-t-lg shrink-0 transition ${
                      selectedPartIdx === i
                        ? 'bg-indigo-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {String.fromCharCode(65 + i)}: {p.name.slice(0, 10)}
                  </button>
                ))}
              </div>

              {/* Selected part editor */}
              <div className="flex-1 overflow-y-auto p-4">
                {selectedPartIdx === null ? (
                  <p className="text-sm text-gray-400 text-center mt-8">Select a part tab to edit</p>
                ) : (
                  <PartEditor
                    part={asm.parts[selectedPartIdx]}
                    partIndex={selectedPartIdx}
                    onChange={(updated) => updatePart(selectedPartIdx, updated)}
                    onRemove={() => removePart(selectedPartIdx)}
                  />
                )}
              </div>
            </>
          )}
        </div>

        {/* Right: Live canvas preview (BUG A fix) */}
        <div className="w-1/2 bg-slate-100 flex flex-col overflow-hidden">
          <div className="bg-slate-800 text-white px-4 py-2 text-xs font-bold flex justify-between items-center shrink-0">
            <span>Drawing Preview</span>
            <span className="text-slate-400 text-xs">Live · updates as you edit</span>
          </div>
          <div className="flex-1 flex items-center justify-center p-2">
            <canvas
              ref={canvasRef}
              width={480}
              height={320}
              className="rounded bg-white shadow border border-gray-200 w-full h-full"
              style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
            />
          </div>
          {previewError && (
            <p className="text-xs text-red-500 text-center pb-2">{previewError}</p>
          )}
        </div>
      </div>
    </div>
  );
};

// ─── Part Editor ─────────────────────────────────────────────────────────────

const PartEditor = ({
  part, partIndex, onChange, onRemove,
}: {
  part: Part;
  partIndex: number;
  onChange: (p: Part) => void;
  onRemove: () => void;
}) => {
  const [activeSection, setActiveSection] = useState<'dims' | 'edges' | 'cutouts' | 'holes' | 'splashes'>('dims');

  const updateDim = (field: 'length' | 'depth' | 'thickness', val: number) => {
    onChange({ ...part, dimensions: { ...part.dimensions, [field]: val } });
  };

  // --- Edges ---
  const addEdge = () => {
    onChange({ ...part, edges: [...part.edges, { position: Position.FRONT, edge_type: EdgeType.EASED }] });
  };
  const updateEdge = (i: number, field: string, val: string) => {
    const edges = [...part.edges];
    edges[i] = { ...edges[i], [field]: val };
    onChange({ ...part, edges });
  };
  const removeEdge = (i: number) => {
    const edges = [...part.edges];
    edges.splice(i, 1);
    onChange({ ...part, edges });
  };

  // --- Cutouts ---
  const addCutout = () => {
    const newCutout: Cutout = {
      cutout_type: CutoutType.SINK,
      mount_type: MountType.UNDERMOUNT,
      dimensions: { length: 24, depth: 18 },
      center_x: part.dimensions.length / 2,
      center_y: part.dimensions.depth / 2,
    };
    onChange({ ...part, cutouts: [...part.cutouts, newCutout] });
  };
  const updateCutout = (i: number, field: string, val: string | number) => {
    const cutouts = [...part.cutouts];
    cutouts[i] = { ...cutouts[i], [field]: val };
    onChange({ ...part, cutouts });
  };
  const updateCutoutDim = (i: number, field: 'length' | 'depth', val: number) => {
    const cutouts = [...part.cutouts];
    cutouts[i] = { ...cutouts[i], dimensions: { ...cutouts[i].dimensions, [field]: val } };
    onChange({ ...part, cutouts });
  };
  const removeCutout = (i: number) => {
    const cutouts = [...part.cutouts];
    cutouts.splice(i, 1);
    onChange({ ...part, cutouts });
  };

  // --- Holes ---
  const addHole = () => {
    const newHole: Hole = {
      diameter: 1.5,
      center_x: part.dimensions.length / 2,
      center_y: part.dimensions.depth / 2,
      purpose: 'Faucet',
    };
    onChange({ ...part, holes: [...part.holes, newHole] });
  };
  const updateHole = (i: number, field: string, val: string | number) => {
    const holes = [...part.holes];
    holes[i] = { ...holes[i], [field]: val };
    onChange({ ...part, holes });
  };
  const removeHole = (i: number) => {
    const holes = [...part.holes];
    holes.splice(i, 1);
    onChange({ ...part, holes });
  };

  // --- Splashes ---
  const addSplash = () => {
    const newSplash: Splash = {
      splash_type: SplashType.BACKSPLASH,
      dimensions: { length: part.dimensions.length, depth: 4 },
    };
    onChange({ ...part, splashes: [...part.splashes, newSplash] });
  };
  const updateSplash = (i: number, field: string, val: string | number) => {
    const splashes = [...part.splashes];
    splashes[i] = { ...splashes[i], [field]: val };
    onChange({ ...part, splashes });
  };
  const updateSplashDim = (i: number, field: 'length' | 'depth', val: number) => {
    const splashes = [...part.splashes];
    splashes[i] = { ...splashes[i], dimensions: { ...splashes[i].dimensions, [field]: val } };
    onChange({ ...part, splashes });
  };
  const removeSplash = (i: number) => {
    const splashes = [...part.splashes];
    splashes.splice(i, 1);
    onChange({ ...part, splashes });
  };

  const sections = [
    { id: 'dims' as const, label: 'Dimensions', count: 0 },
    { id: 'edges' as const, label: 'Edges', count: part.edges.length },
    { id: 'cutouts' as const, label: 'Cutouts', count: part.cutouts.length },
    { id: 'holes' as const, label: 'Holes', count: part.holes.length },
    { id: 'splashes' as const, label: 'Splashes', count: part.splashes.length },
  ];

  return (
    <div className="space-y-3">
      {/* Part header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-bold text-gray-800">
            Part {String.fromCharCode(65 + partIndex)}
          </p>
        </div>
        <button onClick={onRemove} className="text-red-500 hover:text-red-700 text-xs font-medium">
          Remove
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs font-bold text-gray-600 mb-1">Name</label>
          <input
            type="text"
            value={part.name}
            onChange={(e) => onChange({ ...part, name: e.target.value })}
            className="w-full border border-gray-300 p-1.5 text-sm rounded-lg"
          />
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-600 mb-1">Type</label>
          <select
            value={part.part_type}
            onChange={(e) => onChange({ ...part, part_type: e.target.value as PartType })}
            className="w-full border border-gray-300 p-1.5 text-sm rounded-lg bg-white"
          >
            {Object.values(PartType).map((t) => (
              <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Section tabs */}
      <div className="flex gap-1 flex-wrap">
        {sections.map((s) => (
          <button
            key={s.id}
            onClick={() => setActiveSection(s.id)}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg transition ${
              activeSection === s.id
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {s.label}{s.count > 0 ? ` (${s.count})` : ''}
          </button>
        ))}
      </div>

      {/* Dimensions */}
      {activeSection === 'dims' && (
        <div className="bg-gray-50 rounded-lg p-3 space-y-2">
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="block text-xs font-bold text-gray-600 mb-1">Length (in)</label>
              <input
                type="number"
                step="0.125"
                value={part.dimensions.length}
                onChange={(e) => updateDim('length', parseFloat(e.target.value) || 0)}
                className="w-full border border-gray-300 p-1.5 text-sm rounded-lg"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-600 mb-1">Depth (in)</label>
              <input
                type="number"
                step="0.125"
                value={part.dimensions.depth}
                onChange={(e) => updateDim('depth', parseFloat(e.target.value) || 0)}
                className="w-full border border-gray-300 p-1.5 text-sm rounded-lg"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-600 mb-1">Thickness (in)</label>
              <input
                type="number"
                step="0.125"
                value={part.dimensions.thickness ?? ''}
                placeholder="3CM"
                onChange={(e) => updateDim('thickness', parseFloat(e.target.value) || 0)}
                className="w-full border border-gray-300 p-1.5 text-sm rounded-lg"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-bold text-gray-600 mb-1">Notes</label>
            <input
              type="text"
              value={part.notes || ''}
              onChange={(e) => onChange({ ...part, notes: e.target.value })}
              placeholder="e.g., verify field dimensions before cut"
              className="w-full border border-gray-300 p-1.5 text-sm rounded-lg"
            />
          </div>
          <p className="text-xs text-gray-400">
            Area: {(part.dimensions.length * part.dimensions.depth / 144).toFixed(2)} sq ft
          </p>
        </div>
      )}

      {/* Edges */}
      {activeSection === 'edges' && (
        <div className="bg-gray-50 rounded-lg p-3 space-y-2">
          <div className="flex justify-between items-center">
            <p className="text-xs font-bold text-gray-600">Edge Treatments</p>
            <button onClick={addEdge} className="text-xs text-indigo-600 hover:underline font-medium">
              + Add Edge
            </button>
          </div>
          {part.edges.length === 0 && (
            <p className="text-xs text-gray-400">No edges defined. Add an edge treatment for exposed edges.</p>
          )}
          {part.edges.map((e, i) => (
            <div key={i} className="flex gap-2 items-center bg-white rounded-lg p-2 border border-gray-200">
              <select
                value={e.position}
                onChange={(ev) => updateEdge(i, 'position', ev.target.value)}
                className="flex-1 border border-gray-300 p-1 text-xs rounded-lg bg-white"
              >
                {Object.values(Position).map((p) => (
                  <option key={p} value={p}>{p.toUpperCase()}</option>
                ))}
              </select>
              <select
                value={e.edge_type}
                onChange={(ev) => updateEdge(i, 'edge_type', ev.target.value)}
                className="flex-1 border border-gray-300 p-1 text-xs rounded-lg bg-white"
              >
                {Object.values(EdgeType).map((t) => (
                  <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                ))}
              </select>
              <button onClick={() => removeEdge(i)} className="text-red-500 text-sm font-bold w-5 text-center">×</button>
            </div>
          ))}
        </div>
      )}

      {/* Cutouts */}
      {activeSection === 'cutouts' && (
        <div className="bg-gray-50 rounded-lg p-3 space-y-2">
          <div className="flex justify-between items-center">
            <p className="text-xs font-bold text-gray-600">Cutouts (Sinks / Cooktops)</p>
            <button onClick={addCutout} className="text-xs text-indigo-600 hover:underline font-medium">
              + Add Cutout
            </button>
          </div>
          {part.cutouts.length === 0 && (
            <p className="text-xs text-gray-400">No cutouts. Add sink or cooktop openings.</p>
          )}
          {part.cutouts.map((co, i) => (
            <div key={i} className="bg-white rounded-lg p-3 border border-gray-200 space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs font-bold text-gray-700">Cutout {i + 1}</p>
                <button onClick={() => removeCutout(i)} className="text-red-500 text-xs font-medium">Remove</button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-gray-500 mb-0.5">Type</label>
                  <select
                    value={co.cutout_type}
                    onChange={(e) => updateCutout(i, 'cutout_type', e.target.value)}
                    className="w-full border border-gray-300 p-1 text-xs rounded-lg bg-white"
                  >
                    {Object.values(CutoutType).map((t) => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-0.5">Mount</label>
                  <select
                    value={co.mount_type}
                    onChange={(e) => updateCutout(i, 'mount_type', e.target.value)}
                    className="w-full border border-gray-300 p-1 text-xs rounded-lg bg-white"
                  >
                    {Object.values(MountType).map((t) => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-0.5">Length (in)</label>
                  <input
                    type="number" step="0.25"
                    value={co.dimensions.length}
                    onChange={(e) => updateCutoutDim(i, 'length', parseFloat(e.target.value) || 0)}
                    className="w-full border border-gray-300 p-1 text-xs rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-0.5">Depth (in)</label>
                  <input
                    type="number" step="0.25"
                    value={co.dimensions.depth}
                    onChange={(e) => updateCutoutDim(i, 'depth', parseFloat(e.target.value) || 0)}
                    className="w-full border border-gray-300 p-1 text-xs rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-0.5">Center X (in)</label>
                  <input
                    type="number" step="0.25"
                    value={co.center_x}
                    onChange={(e) => updateCutout(i, 'center_x', parseFloat(e.target.value) || 0)}
                    className="w-full border border-gray-300 p-1 text-xs rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-0.5">Center Y (in)</label>
                  <input
                    type="number" step="0.25"
                    value={co.center_y}
                    onChange={(e) => updateCutout(i, 'center_y', parseFloat(e.target.value) || 0)}
                    className="w-full border border-gray-300 p-1 text-xs rounded-lg"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Holes */}
      {activeSection === 'holes' && (
        <div className="bg-gray-50 rounded-lg p-3 space-y-2">
          <div className="flex justify-between items-center">
            <p className="text-xs font-bold text-gray-600">Holes (Faucet / Drain)</p>
            <button onClick={addHole} className="text-xs text-indigo-600 hover:underline font-medium">
              + Add Hole
            </button>
          </div>
          {part.holes.length === 0 && (
            <p className="text-xs text-gray-400">No holes. Add faucet or drain holes.</p>
          )}
          {part.holes.map((h, i) => (
            <div key={i} className="bg-white rounded-lg p-3 border border-gray-200 space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs font-bold text-gray-700">Hole {i + 1}</p>
                <button onClick={() => removeHole(i)} className="text-red-500 text-xs font-medium">Remove</button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-gray-500 mb-0.5">Purpose</label>
                  <input
                    type="text"
                    value={h.purpose}
                    onChange={(e) => updateHole(i, 'purpose', e.target.value)}
                    placeholder="Faucet"
                    className="w-full border border-gray-300 p-1 text-xs rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-0.5">Diameter (in)</label>
                  <input
                    type="number" step="0.125"
                    value={h.diameter}
                    onChange={(e) => updateHole(i, 'diameter', parseFloat(e.target.value) || 0)}
                    className="w-full border border-gray-300 p-1 text-xs rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-0.5">Center X (in)</label>
                  <input
                    type="number" step="0.25"
                    value={h.center_x}
                    onChange={(e) => updateHole(i, 'center_x', parseFloat(e.target.value) || 0)}
                    className="w-full border border-gray-300 p-1 text-xs rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-0.5">Center Y (in)</label>
                  <input
                    type="number" step="0.25"
                    value={h.center_y}
                    onChange={(e) => updateHole(i, 'center_y', parseFloat(e.target.value) || 0)}
                    className="w-full border border-gray-300 p-1 text-xs rounded-lg"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Splashes */}
      {activeSection === 'splashes' && (
        <div className="bg-gray-50 rounded-lg p-3 space-y-2">
          <div className="flex justify-between items-center">
            <p className="text-xs font-bold text-gray-600">Splash Bands</p>
            <button onClick={addSplash} className="text-xs text-indigo-600 hover:underline font-medium">
              + Add Splash
            </button>
          </div>
          {part.splashes.length === 0 && (
            <p className="text-xs text-gray-400">No splashes. Add backsplash or side-splash.</p>
          )}
          {part.splashes.map((sp, i) => (
            <div key={i} className="bg-white rounded-lg p-3 border border-gray-200 space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs font-bold text-gray-700">Splash {i + 1}</p>
                <button onClick={() => removeSplash(i)} className="text-red-500 text-xs font-medium">Remove</button>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-xs text-gray-500 mb-0.5">Type</label>
                  <select
                    value={sp.splash_type}
                    onChange={(e) => updateSplash(i, 'splash_type', e.target.value)}
                    className="w-full border border-gray-300 p-1 text-xs rounded-lg bg-white"
                  >
                    {Object.values(SplashType).map((t) => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-0.5">Length (in)</label>
                  <input
                    type="number" step="0.25"
                    value={sp.dimensions.length}
                    onChange={(e) => updateSplashDim(i, 'length', parseFloat(e.target.value) || 0)}
                    className="w-full border border-gray-300 p-1 text-xs rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-0.5">Height (in)</label>
                  <input
                    type="number" step="0.25"
                    value={sp.dimensions.depth}
                    onChange={(e) => updateSplashDim(i, 'depth', parseFloat(e.target.value) || 0)}
                    className="w-full border border-gray-300 p-1 text-xs rounded-lg"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
