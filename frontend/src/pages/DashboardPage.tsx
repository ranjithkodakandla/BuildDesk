import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import { Project, ProjectStatus } from '../types/hierarchy';
import { useAuthStore } from '../store/authStore';
import { OperationalQueuesPanel } from '../components/OperationalQueuesPanel';
import { SearchPanel } from '../components/SearchPanel';
import { TenantSettingsPanel } from '../components/TenantSettingsPanel';

type DashboardView = 'projects' | 'search' | 'queues' | 'settings';

const STATUS_CONFIG: Record<string, { label: string; cls: string; dot: string }> = {
  draft:       { label: 'Draft',       cls: 'bg-slate-100 text-slate-600',  dot: 'bg-slate-400'  },
  in_progress: { label: 'In Progress', cls: 'bg-amber-100 text-amber-800',  dot: 'bg-amber-400'  },
  issued:      { label: 'Issued',      cls: 'bg-green-100 text-green-800',  dot: 'bg-green-500'  },
  archived:    { label: 'Archived',    cls: 'bg-gray-100 text-gray-500',    dot: 'bg-gray-300'   },
};

function relativeDate(isoStr: string): string {
  const days = Math.floor((Date.now() - new Date(isoStr).getTime()) / 86_400_000);
  if (days === 0) return 'Today';
  if (days === 1) return '1 day ago';
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return months === 1 ? '1 month ago' : `${months} months ago`;
}

const NAV: { id: DashboardView; label: string }[] = [
  { id: 'projects', label: 'Jobs'      },
  { id: 'queues',   label: 'Issues'    },
  { id: 'search',   label: 'Search'    },
  { id: 'settings', label: 'Settings'  },
];

export const DashboardPage: React.FC = () => {
  const [projects, setProjects]         = useState<Project[]>([]);
  const [loading, setLoading]           = useState(true);
  const [activeView, setActiveView]     = useState<DashboardView>('projects');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newName, setNewName]           = useState('');
  const [newClient, setNewClient]       = useState('');
  const [newMaterial, setNewMaterial]   = useState('');
  const [newAddress, setNewAddress]     = useState('');
  const [newJobNumber, setNewJobNumber] = useState('');
  const [newThickness, setNewThickness] = useState('3CM');
  const [creating, setCreating]         = useState(false);
  const navigate = useNavigate();
  const { logout, user } = useAuthStore();

  const openCreate = () => {
    setNewName(''); setNewClient(''); setNewMaterial(''); setNewAddress('');
    setNewJobNumber(''); setNewThickness('3CM');
    setShowCreateModal(true);
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      // Store job_number + thickness in description as JSON so PDF can read them
      const extraMeta = JSON.stringify({
        job_number: newJobNumber.trim(),
        thickness:  newThickness,
      });
      const proj = await projectsApi.createProject({
        name:         newName.trim(),
        client_name:  newClient.trim()   || undefined,
        material:     newMaterial.trim() || undefined,
        address:      newAddress.trim()  || undefined,
        description:  extraMeta,
        status:       ProjectStatus.DRAFT,
        hierarchy_config: { has_buildings: false, has_floors: false, has_unit_types: true },
      });
      setShowCreateModal(false);
      navigate(`/projects/${proj.project_id}`);
    } catch (err) {
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  useEffect(() => {
    projectsApi.listProjects()
      .then(setProjects)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const active   = projects.filter((p) => p.status === ProjectStatus.IN_PROGRESS || p.status === ProjectStatus.DRAFT);
  const issued   = projects.filter((p) => p.status === ProjectStatus.ISSUED);
  const archived = projects.filter((p) => p.status === ProjectStatus.ARCHIVED);

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-[#e2e8f0] px-6 py-0">
        <div className="flex items-center justify-between h-12 max-w-7xl mx-auto w-full">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded bg-[#1e293b] flex items-center justify-center shrink-0">
              <span className="text-white font-bold text-xs">B</span>
            </div>
            <div>
              <h1 className="text-sm font-bold text-[#1e293b] leading-none">BuildDesk</h1>
              <p className="text-[10px] text-[#94a3b8] leading-none mt-0.5">Countertop Fabrication</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {user?.email && (
              <span className="text-xs text-[#94a3b8] hidden md:block">{user.email}</span>
            )}
            <button
              onClick={openCreate}
              className="btn-primary text-xs px-3 py-1.5"
            >
              + New Job
            </button>
            <button
              onClick={logout}
              className="px-3 py-1.5 border border-[#e2e8f0] text-[#475569] text-xs rounded hover:bg-[#f8fafc] transition"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* ── Nav ─────────────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-[#e2e8f0] px-6">
        <div className="max-w-7xl mx-auto flex gap-0">
          {NAV.map((v) => (
            <button
              key={v.id}
              onClick={() => setActiveView(v.id)}
              className={`px-4 py-3 text-xs font-medium border-b-2 transition-colors ${
                activeView === v.id
                  ? 'border-[#1e293b] text-[#1e293b]'
                  : 'border-transparent text-[#64748b] hover:text-[#334155]'
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Content ─────────────────────────────────────────────────────── */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-5">

        {activeView === 'search' && (
          <SearchPanel onOpenProject={(id) => navigate(`/projects/${id}`)} />
        )}
        {activeView === 'queues' && (
          <OperationalQueuesPanel onOpenProject={(id) => navigate(`/projects/${id}`)} />
        )}
        {activeView === 'settings' && <TenantSettingsPanel />}

        {activeView === 'projects' && (
          loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 animate-pulse">
              {[1, 2, 3].map((i) => <div key={i} className="h-36 bg-[#f1f5f9] rounded" />)}
            </div>
          ) : projects.length === 0 ? (
            <EmptyState onCreate={openCreate} />
          ) : (
            <div className="space-y-6">
              {active.length > 0 && (
                <ProjectGroup
                  title="Active Jobs"
                  projects={active}
                  onOpen={(id) => navigate(`/projects/${id}`)}
                />
              )}
              {issued.length > 0 && (
                <ProjectGroup
                  title="Issued"
                  projects={issued}
                  onOpen={(id) => navigate(`/projects/${id}`)}
                />
              )}
              {archived.length > 0 && (
                <ProjectGroup
                  title="Archived"
                  projects={archived}
                  onOpen={(id) => navigate(`/projects/${id}`)}
                />
              )}
            </div>
          )
        )}
      </main>

      {/* ── Create modal ─────────────────────────────────────────────────── */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded border border-[#e2e8f0] p-5 w-full max-w-sm shadow-xl">
            <h3 className="text-sm font-bold text-[#1e293b] mb-1">New Fabrication Job</h3>
            <p className="text-xs text-[#64748b] mb-4">Fill in the job details — you can edit these later.</p>

            <div className="space-y-3">
              <Field label="Job / Project Name *" hint="e.g. Haven On Main Phase 2">
                <input
                  data-testid="create-project-name"
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && newName.trim() && handleCreate()}
                  placeholder="Haven On Main Phase 2"
                  autoFocus
                  className="input-field"
                />
              </Field>
              <Field label="Builder / Client" hint="Who is this job for?">
                <input
                  data-testid="create-project-client"
                  type="text"
                  value={newClient}
                  onChange={(e) => setNewClient(e.target.value)}
                  placeholder="Meritage Homes"
                  className="input-field"
                />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Material Color" hint="e.g. Black Pearl">
                  <input
                    data-testid="create-project-material"
                    type="text"
                    value={newMaterial}
                    onChange={(e) => setNewMaterial(e.target.value)}
                    placeholder="Black Pearl"
                    className="input-field"
                  />
                </Field>
                <Field label="Thickness">
                  <select
                    value={newThickness}
                    onChange={e => setNewThickness(e.target.value)}
                    className="input-field"
                  >
                    <option value="2CM">2CM (3/4")</option>
                    <option value="3CM">3CM (1-1/4")</option>
                    <option value="2CM & 3CM">2CM &amp; 3CM (mixed)</option>
                  </select>
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Job / PO Number" hint="e.g. 1041">
                  <input
                    type="text"
                    value={newJobNumber}
                    onChange={(e) => setNewJobNumber(e.target.value)}
                    placeholder="1041"
                    className="input-field"
                  />
                </Field>
                <Field label="Location" hint="City, State">
                  <input
                    type="text"
                    value={newAddress}
                    onChange={(e) => setNewAddress(e.target.value)}
                    placeholder="Lafayette, IN"
                    className="input-field"
                  />
                </Field>
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-3 py-1.5 border border-[#e2e8f0] text-[#475569] text-xs rounded hover:bg-[#f8fafc] transition"
              >
                Cancel
              </button>
              <button
                data-testid="create-project-submit"
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
                className="btn-primary text-xs px-4 py-1.5 disabled:opacity-50"
              >
                {creating ? 'Creating…' : 'Create Job →'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ── Sub-components ─────────────────────────────────────────────────────────

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
  <div>
    <label className="flex items-baseline gap-2 text-xs font-medium text-[#334155] mb-1">
      {label}
      {hint && <span className="font-normal text-[#94a3b8]">{hint}</span>}
    </label>
    {children}
  </div>
);

const ProjectGroup: React.FC<{
  title: string;
  projects: Project[];
  onOpen: (id: string) => void;
}> = ({ title, projects, onOpen }) => (
  <div>
    <p className="text-xs font-bold text-[#94a3b8] uppercase tracking-widest mb-2.5">{title}</p>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {projects.map((p) => (
        <ProjectCard key={p.project_id} project={p} onClick={() => onOpen(p.project_id)} />
      ))}
    </div>
  </div>
);

const ProjectCard: React.FC<{ project: Project; onClick: () => void }> = ({ project, onClick }) => {
  const sc = STATUS_CONFIG[project.status] || STATUS_CONFIG['draft'];

  return (
    <div
      onClick={onClick}
      className="bg-white rounded border border-[#e2e8f0] hover:border-[#94a3b8] cursor-pointer transition-all p-4 group flex flex-col"
    >
      {/* Top row: status badge + date */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full shrink-0 ${sc.dot}`} />
          <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded ${sc.cls}`}>{sc.label}</span>
        </div>
        <span className="text-[10px] text-[#94a3b8]">{relativeDate(project.created_at)}</span>
      </div>

      {/* Project name */}
      <h3 className="text-sm font-bold text-[#1e293b] group-hover:text-[#334155] leading-tight mb-1.5 truncate">
        {project.name}
      </h3>

      {/* Meta */}
      <div className="space-y-0.5 flex-1">
        {project.client_name && (
          <p className="text-xs text-[#475569] truncate">
            <span className="text-[#94a3b8] mr-1">Builder</span>
            <span className="font-medium">{project.client_name}</span>
          </p>
        )}
        {project.material && (
          <p className="text-xs text-[#64748b] truncate">{project.material}</p>
        )}
        {project.address && (
          <p className="text-[10px] text-[#94a3b8] truncate">{project.address}</p>
        )}
      </div>

      {/* Footer */}
      <div className="mt-2.5 pt-2 border-t border-[#f1f5f9] flex items-center justify-between">
        <span className="text-[10px] text-[#94a3b8]">
          {project.issue_date
            ? `Issue: ${new Date(project.issue_date).toLocaleDateString()}`
            : 'No issue date'}
        </span>
        <span className="text-xs text-[#64748b] font-medium opacity-0 group-hover:opacity-100 transition-opacity">
          Open →
        </span>
      </div>
    </div>
  );
};

const EmptyState: React.FC<{ onCreate: () => void }> = ({ onCreate }) => (
  <div className="bg-white rounded border border-dashed border-[#cbd5e1] p-12 text-center max-w-md mx-auto">
    <h3 className="text-sm font-bold text-[#1e293b] mb-1">No jobs yet</h3>
    <p className="text-xs text-[#64748b] mb-4 max-w-xs mx-auto">
      Create your first fabrication job to start building unit schedules and generating shop drawing packages.
    </p>
    <button
      onClick={onCreate}
      className="btn-primary text-xs px-4 py-1.5"
    >
      Create First Job →
    </button>
  </div>
);
