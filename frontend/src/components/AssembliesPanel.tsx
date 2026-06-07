import React, { useEffect, useState } from 'react';
import { Project, UnitType, UnitVariant } from '../types/hierarchy';
import { Assembly, AssemblyType, EdgeType, Part, PartType, Position, SplashType } from '../types/fabrication';
import { assembliesApi } from '../api/assemblies';
import { projectsApi } from '../api/projects';
import { AssemblyEditor } from './AssemblyEditor';
import { templatesApi } from '../api/templates';
import { tenantApi } from '../api/tenant';

// ── Parse extra metadata stored in Project.description as JSON ───────────────
function parseProjectExtra(description?: string | null) {
  try { return JSON.parse(description ?? '{}'); }
  catch { return {}; }
}

// ── Assembly → drawing dict (for industry-standard PDF) ──────────────────────
function assemblyToDrawingDict(asm: Assembly, units?: string[]): Record<string, unknown> {
  // Parse ticket number from first note if present
  const firstNote = (asm.notes as unknown as Array<{content: string}> | undefined)?.[0]?.content ?? '';
  const ticketMatch = firstNote.match(/ticket[:#\s]+([^\s|]+)/i);
  const ticketNumber = ticketMatch ? ticketMatch[1] : '';

  const parts = (asm.parts ?? []).map((p: Part, i: number) => {
    const edgeMap: Record<string, string> = {};
    (p.edges ?? []).forEach(e => { edgeMap[e.position] = e.edge_type; });
    return {
      label: String.fromCharCode(65 + i),
      width: p.dimensions.length,
      depth: p.dimensions.depth,
      edges: {
        front: edgeMap['front'] ?? 'eased',
        back:  edgeMap['back']  ?? 'raw',
        left:  edgeMap['left']  ?? 'eased',
        right: edgeMap['right'] ?? 'eased',
      },
      cutouts: (p.cutouts ?? []).map(co => ({
        mountType:   co.mount_type.replace('_', ' '),
        sinkType:    co.cutout_type,
        sinkLabel:   co.cutout_type === 'sink' ? 'China Bowl' : co.cutout_type.replace('_', ' '),
        width:       co.dimensions.length,
        height:      co.dimensions.depth,
        xOffset:     Math.max(0, co.center_x - co.dimensions.length / 2),
        yOffset:     Math.max(0, co.center_y - co.dimensions.depth / 2),
        // Model number: check notes field (stored as "Model #CS-1417")
        modelNumber: (co.notes ?? '').replace(/model\s*#?\s*/i, '').trim(),
      })),
      holes: (p.holes ?? []).map(h => ({
        type:     h.purpose ?? 'faucet',
        diameter: h.diameter,
        x:        h.center_x,
        y:        h.center_y,
      })),
      splashes: (p.splashes ?? []).map(sp => ({
        side:   sp.splash_type === SplashType.BACKSPLASH   ? 'back'
               : sp.splash_type === SplashType.LEFT_SPLASH  ? 'left' : 'right',
        height: sp.dimensions.depth,
        length: sp.dimensions.length,
      })),
      cornerRadius: 0.5,
    };
  });

  return {
    name:         asm.name,
    roomType:     asm.assembly_type,
    ticketNumber: ticketNumber,
    scale:        '3/4" = 1\'-0"',
    pageNumber:   1,
    units:        units ?? [],
    parts,
    seams:        [],
  };
}

function projectToDict(
  project: Project,
  companyExtra?: { address1?: string; address2?: string; phone?: string; drawn_by?: string }
): Record<string, unknown> {
  const extra = parseProjectExtra((project as unknown as Record<string, string>).description);
  return {
    name:      project.name,
    location:  project.address ?? '',
    material:  project.material ?? '',
    thickness: extra.thickness ?? '3CM',
    issueDate: project.issue_date ?? null,
    drawnBy:   companyExtra?.drawn_by ?? extra.drawn_by ?? '',
    jobNumber: extra.job_number ?? project.project_id.slice(0, 8),
    company: {
      name:     companyExtra ? (project.client_name ?? 'Your Company') : 'Your Company',
      address1: companyExtra?.address1 ?? '',
      address2: companyExtra?.address2 ?? '',
      phone:    companyExtra?.phone    ?? '',
    },
  };
}

// ── Template quick-start definitions (BUG B fix) ────────────────────────────
interface DrawingTemplate {
  id: string;
  label: string;
  type: AssemblyType;
  parts: Array<{ name: string; partType: PartType; exposedEdges: Position[]; seamEdges: Position[] }>;
}

const DRAWING_TEMPLATES: DrawingTemplate[] = [
  {
    id: 'straight',
    label: 'Straight Kitchen',
    type: AssemblyType.KITCHEN,
    parts: [
      { name: 'Part A', partType: PartType.MAIN_TOP,
        exposedEdges: [Position.FRONT, Position.LEFT, Position.RIGHT],
        seamEdges: [] },
    ],
  },
  {
    id: 'l_shape',
    label: 'L-Shape Kitchen',
    type: AssemblyType.KITCHEN,
    parts: [
      { name: 'Part A', partType: PartType.MAIN_TOP,
        exposedEdges: [Position.FRONT, Position.LEFT],
        seamEdges: [Position.RIGHT] },
      { name: 'Part B', partType: PartType.RIGHT_RETURN,
        exposedEdges: [Position.FRONT, Position.RIGHT],
        seamEdges: [Position.LEFT] },
    ],
  },
  {
    id: 'u_shape',
    label: 'U-Shape Kitchen',
    type: AssemblyType.KITCHEN,
    parts: [
      { name: 'Part A', partType: PartType.MAIN_TOP,
        exposedEdges: [Position.FRONT],
        seamEdges: [Position.LEFT, Position.RIGHT] },
      { name: 'Part B', partType: PartType.LEFT_RETURN,
        exposedEdges: [Position.FRONT, Position.LEFT],
        seamEdges: [Position.RIGHT] },
      { name: 'Part C', partType: PartType.RIGHT_RETURN,
        exposedEdges: [Position.FRONT, Position.RIGHT],
        seamEdges: [Position.LEFT] },
    ],
  },
  {
    id: 'vanity',
    label: 'Vanity Top',
    type: AssemblyType.VANITY,
    parts: [
      { name: 'Part A', partType: PartType.MAIN_TOP,
        exposedEdges: [Position.FRONT, Position.LEFT, Position.RIGHT],
        seamEdges: [] },
    ],
  },
  {
    id: 'island',
    label: 'Island',
    type: AssemblyType.ISLAND,
    parts: [
      { name: 'Part A', partType: PartType.MAIN_TOP,
        exposedEdges: [Position.FRONT, Position.BACK, Position.LEFT, Position.RIGHT],
        seamEdges: [] },
    ],
  },
];

function buildPartsFromTemplate(tmpl: DrawingTemplate): Part[] {
  return tmpl.parts.map(def => ({
    part_type: def.partType,
    name: def.name,
    dimensions: { length: 60, depth: 25.5 },
    edges: [
      ...def.exposedEdges.map(pos => ({ position: pos, edge_type: EdgeType.EASED })),
      ...def.seamEdges.map(pos => ({ position: pos, edge_type: EdgeType.RAW })),
      // Raw back edge by default where not specified
      ...([Position.FRONT, Position.BACK, Position.LEFT, Position.RIGHT]
          .filter(p => !def.exposedEdges.includes(p) && !def.seamEdges.includes(p))
          .map(pos => ({ position: pos, edge_type: EdgeType.RAW }))),
    ],
    cutouts: [],
    holes: [],
    splashes: [],
  }));
}

interface Props {
  project: Project;
}

export const AssembliesPanel: React.FC<Props> = ({ project }) => {
  const [assemblies, setAssemblies] = useState<Assembly[]>([]);
  const [unitTypes, setUnitTypes] = useState<UnitType[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [justSavedId, setJustSavedId] = useState<string | null>(null);

  const [isCreating, setIsCreating] = useState(false);
  const [newAsmName, setNewAsmName] = useState('');
  const [newAsmType, setNewAsmType] = useState<AssemblyType>(AssemblyType.KITCHEN);
  const [newAsmUnitTypeId, setNewAsmUnitTypeId] = useState<string>('');
  const [creating, setCreating] = useState(false);

  // BUG B: template quick-start
  const [pendingTemplateParts, setPendingTemplateParts] = useState<Part[] | null>(null);

  // BUG C: apply-to-all-units state
  const [applyTarget, setApplyTarget] = useState<Assembly | null>(null);
  const [applying, setApplying] = useState(false);
  const [applyConfirm, setApplyConfirm] = useState(false);
  const [totalUnits, setTotalUnits] = useState(0);

  // PDF download per assembly
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

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
      // Approximate unit count from project hierarchy
      try {
        const units = await projectsApi.listUnits(project.project_id);
        setTotalUnits(units.length);
      } catch {
        setTotalUnits(utList.length);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [project.project_id]);

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
        parts: pendingTemplateParts ?? [],
        notes: [],
      });
      setAssemblies((prev) => [...prev, created]);
      setIsCreating(false);
      setNewAsmName('');
      setPendingTemplateParts(null);
      setSelectedId(created.assembly_id || null);
      setEditing(true);
    } catch (e) {
      console.error(e);
    } finally {
      setCreating(false);
    }
  };

  // BUG B: create from template card click
  const handleTemplateClick = (tmpl: DrawingTemplate) => {
    setPendingTemplateParts(buildPartsFromTemplate(tmpl));
    setNewAsmType(tmpl.type);
    setNewAsmName(tmpl.label);
    setIsCreating(true);
  };

  // Download industry-standard PDF for a single assembly
  const handleDownloadPdf = async (asm: Assembly) => {
    if (!asm.assembly_id) return;
    setDownloadingId(asm.assembly_id);
    try {
      const [full, tenantProfile] = await Promise.all([
        assembliesApi.getAssembly(asm.assembly_id),
        tenantApi.getProfile(),
      ]);
      // Parse company extra (address, phone, drawn_by) from standard_notes
      let companyExtra: { address1?: string; address2?: string; phone?: string; drawn_by?: string } = {};
      try { companyExtra = JSON.parse(tenantProfile.standard_notes ?? '{}'); } catch { /* ignore */ }

      // Set company name from tenant profile
      companyExtra = { ...companyExtra };
      const baseProj = projectToDict(project, companyExtra) as Record<string, unknown>;
      const proj = {
        ...baseProj,
        company: {
          ...(baseProj.company as Record<string, unknown>),
          name: tenantProfile.company_name || project.client_name || 'Your Company',
        },
      };
      const drawing = assemblyToDrawingDict(full, []);
      const blob = await templatesApi.drawingPdf(drawing, proj);
      const url  = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href     = url;
      link.download = `${asm.name.replace(/\s+/g, '_')}.pdf`;
      document.body.appendChild(link); link.click(); link.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('PDF generation failed', e);
    } finally {
      setDownloadingId(null);
    }
  };

  // BUG C: apply drawing to all units that don't have one of this type
  const unitCount = totalUnits;
  const handleApplyToAll = async () => {
    if (!applyTarget?.assembly_id) return;
    setApplying(true);
    try {
      // Duplicate the assembly for each unit that doesn't already have one of this type
      const targetType = applyTarget.assembly_type;
      const existingCount = assemblies.filter(a => a.assembly_type === targetType).length;
      const toCreate = Math.max(0, unitCount - existingCount);
      for (let i = 0; i < toCreate; i++) {
        await assembliesApi.duplicateAssembly(applyTarget.assembly_id, {
          new_name: `${applyTarget.name} (Unit ${i + existingCount + 1})`,
        });
      }
      await loadData();
    } catch (e) {
      console.error(e);
    } finally {
      setApplying(false);
      setApplyTarget(null);
      setApplyConfirm(false);
    }
  };

  const handleEdit = (assemblyId: string) => {
    setSelectedId(assemblyId);
    setEditing(true);
  };

  const handleDuplicate = async (asm: Assembly) => {
    if (!asm.assembly_id) return;
    try {
      const dup = await assembliesApi.duplicateAssembly(asm.assembly_id, {
        new_name: `${asm.name} (Copy)`,
      });
      setAssemblies((prev) => [...prev, dup]);
    } catch (e) {
      console.error(e);
    }
  };

  const sqft = (asm: Assembly) => {
    const total = asm.parts?.reduce(
      (n, p) => n + (p.dimensions.length * p.dimensions.depth / 144),
      0,
    ) ?? 0;
    return total > 0 ? total.toFixed(1) : '—';
  };

  // ── Loading skeleton ────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="space-y-2 animate-pulse">
        <div className="h-8 bg-[#f1f5f9] rounded w-48" />
        <div className="h-14 bg-[#f1f5f9] rounded" />
        <div className="h-14 bg-[#f1f5f9] rounded" />
        <div className="h-14 bg-[#f1f5f9] rounded" />
      </div>
    );
  }

  // ── Assembly editor (full takeover — untouched) ─────────────────────────────
  if (editing && selected) {
    return (
      <AssemblyEditor
        assembly={selected}
        onBack={() => {
          setEditing(false);
          setJustSavedId(selected.assembly_id || null);
          loadData();
          setTimeout(() => setJustSavedId(null), 3000);
        }}
        onSaved={loadData}
      />
    );
  }

  // ── Flat list view ──────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-3 max-w-4xl">
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-[#1e293b]">Drawings</h2>
          <p className="text-xs text-[#64748b]">
            {assemblies.length} drawing{assemblies.length !== 1 ? 's' : ''} · fabrication shop drawings
          </p>
        </div>
        <button
          onClick={() => { setIsCreating(!isCreating); setPendingTemplateParts(null); }}
          className={`px-3 py-1.5 text-xs font-medium rounded transition ${
            isCreating
              ? 'bg-[#f1f5f9] text-[#475569] border border-[#e2e8f0]'
              : 'btn-primary'
          }`}
        >
          {isCreating ? 'Cancel' : '+ New Drawing'}
        </button>
      </div>

      {/* BUG B fix: Template quick-start cards */}
      {!isCreating && assemblies.length === 0 && (
        <div>
          <p className="text-xs font-bold text-[#94a3b8] uppercase tracking-wider mb-2">
            Start from a template
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            {DRAWING_TEMPLATES.map(tmpl => (
              <button
                key={tmpl.id}
                onClick={() => handleTemplateClick(tmpl)}
                className="p-3 rounded border-2 border-[#e2e8f0] bg-white hover:border-indigo-400 hover:shadow-sm text-left transition focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                <p className="text-xs font-semibold text-[#1e293b]">{tmpl.label}</p>
                <p className="text-[10px] text-[#94a3b8] mt-0.5">{tmpl.parts.length} part{tmpl.parts.length !== 1 ? 's' : ''}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Create form */}
      {isCreating && (
        <div className="bg-[#f8fafc] border border-[#e2e8f0] rounded p-3 flex flex-wrap gap-3 items-end">
          <div>
            <label className="label-text">Name</label>
            <input
              type="text"
              value={newAsmName}
              onChange={(e) => setNewAsmName(e.target.value)}
              placeholder="Kitchen A"
              className="input-field w-40"
              autoFocus
            />
          </div>
          <div>
            <label className="label-text">Type</label>
            <select
              value={newAsmType}
              onChange={(e) => setNewAsmType(e.target.value as AssemblyType)}
              className="input-field"
            >
              {Object.values(AssemblyType).map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label-text">
              Unit Type{' '}
              <span className="font-normal text-[#94a3b8]">(optional)</span>
            </label>
            <select
              value={newAsmUnitTypeId}
              onChange={(e) => setNewAsmUnitTypeId(e.target.value)}
              className="input-field w-40"
            >
              <option value="">— Any type —</option>
              {unitTypes.map((ut) => (
                <option key={ut.unit_type_id} value={ut.unit_type_id}>
                  {ut.name || ut.code}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={handleCreate}
            disabled={creating || !newAsmName.trim()}
            className="btn-primary text-xs py-1.5 px-4 disabled:opacity-50"
          >
            {creating ? 'Creating…' : 'Create Drawing'}
          </button>
        </div>
      )}

      {/* BUG C: Apply-to-all confirmation dialog */}
      {applyConfirm && applyTarget && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4">
            <h3 className="text-sm font-bold text-[#1e293b] mb-2">Apply to all units?</h3>
            <p className="text-xs text-[#475569] mb-4">
              Apply <strong>{applyTarget.name}</strong> to all {unitCount} units?
              Won't overwrite existing drawings.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => { setApplyConfirm(false); setApplyTarget(null); }}
                className="text-xs px-4 py-2 rounded border border-[#e2e8f0] text-[#475569] hover:bg-[#f8fafc]"
              >
                Cancel
              </button>
              <button
                onClick={handleApplyToAll}
                disabled={applying}
                className="text-xs px-4 py-2 rounded bg-indigo-600 text-white hover:bg-indigo-700 font-semibold disabled:opacity-50"
              >
                {applying ? 'Applying…' : `Apply to ${unitCount} units`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Flat drawing list */}
      {assemblies.length === 0 ? (
        <div className="border border-dashed border-[#cbd5e1] rounded p-8 text-center">
          <p className="text-sm font-medium text-[#334155] mb-1">No drawings yet</p>
          <p className="text-xs text-[#94a3b8]">
            Save a drawing from Templates, or create one above.
          </p>
        </div>
      ) : (
        <div className="bg-white border border-[#e2e8f0] rounded overflow-hidden">
          {/* Column header */}
          <div className="grid grid-cols-[1fr_auto_auto] gap-3 px-3 py-1.5 bg-[#f8fafc] border-b border-[#e2e8f0]">
            <span className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider">
              Drawing
            </span>
            <span className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider text-right">
              Parts / Sq Ft
            </span>
            <span className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider text-right pr-1">
              Actions
            </span>
          </div>

          {assemblies.map((asm) => {
            const ut = unitTypes.find((t) => t.unit_type_id === asm.unit_type_id);
            const parts = asm.parts?.length ?? 0;
            const isSaved = justSavedId === asm.assembly_id;

            return (
              <div
                key={asm.assembly_id}
                className={`flex items-center gap-3 px-3 py-2.5 border-b border-[#f1f5f9] last:border-0 transition ${
                  isSaved ? 'bg-[#ecfdf5]' : 'hover:bg-[#f8fafc]'
                }`}
              >
                {/* Name + type badge */}
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-[#1e293b] leading-tight truncate">
                    {asm.name}
                  </p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="text-[10px] text-[#94a3b8] capitalize">
                      {asm.assembly_type.replace(/_/g, ' ')}
                    </span>
                    {ut && (
                      <span className="text-[10px] bg-[#f1f5f9] text-[#475569] px-1 py-0.5 rounded font-medium">
                        {ut.code}
                      </span>
                    )}
                    {isSaved && (
                      <span className="text-[10px] text-[#047857] font-medium">✓ saved</span>
                    )}
                  </div>
                </div>

                {/* Stats */}
                <div className="flex gap-3 text-xs text-[#64748b] shrink-0">
                  <span>
                    <b className="text-[#1e293b]">{parts}</b>p
                  </span>
                  <span>
                    <b className="text-[#1e293b]">{sqft(asm)}</b> sqft
                  </span>
                </div>

                {/* Actions */}
                <div className="flex gap-1.5 shrink-0 flex-wrap">
                  {/* BUG C: Apply to all units button (shown after save) */}
                  {isSaved && unitCount > 1 && (
                    <button
                      onClick={() => { setApplyTarget(asm); setApplyConfirm(true); }}
                      className="text-[10px] px-3 py-1 rounded border border-indigo-300 text-indigo-700 bg-indigo-50 hover:bg-indigo-100 font-semibold transition"
                    >
                      Apply to all units ({unitCount})
                    </button>
                  )}
                  <button
                    onClick={() => handleDownloadPdf(asm)}
                    disabled={downloadingId === asm.assembly_id}
                    className="text-[10px] px-3 py-1 rounded border border-[#e2e8f0] text-[#475569] hover:bg-[#f8fafc] transition disabled:opacity-50"
                    title="Download industry-standard shop drawing PDF"
                  >
                    {downloadingId === asm.assembly_id ? '…' : '↓ PDF'}
                  </button>
                  <button
                    onClick={() => asm.assembly_id && handleEdit(asm.assembly_id)}
                    className="btn-primary text-[10px] px-3 py-1"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDuplicate(asm)}
                    className="text-[10px] px-3 py-1 rounded border border-[#e2e8f0] text-[#475569] hover:bg-[#f8fafc] transition"
                  >
                    Dup
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
