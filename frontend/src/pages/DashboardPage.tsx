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
  const [creating, setCreating]         = useState(false);
  const navigate = useNavigate();
  const { logout, user } = useAuthStore();

  const openCreate = () => {
    setNewName(''); setNewClient(''); setNewMaterial(''); setNewAddress('');
    setShowCreateModal(true);
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const proj = await projectsApi.createProject({
        name:         newName.trim(),
        client_name:  newClient.trim()   || undefined,
        material:     newMaterial.trim() || undefined,
        address:      newAddress.trim()  || undefined,
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
    <div className="min-h-screen bg-gray-50 flex flex-col">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200 px-6 py-0">
        <div className="flex items-center justify-between h-14 max-w-7xl mx-auto w-full">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-700 flex items-center justify-center shadow-sm shrink-0">
              <span className="text-white font-black text-sm">B</span>
            </div>
            <div>
              <h1 className="text-base font-bold text-gray-900 leading-none">BuildDesk</h1>
              <p className="text-xs text-gray-400 leading-none mt-0.5">Countertop Fabrication</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {user?.email && (
              <span className="text-xs text-gray-400 hidden md:block">{user.email}</span>
            )}
            <button
              onClick={openCreate}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-xl transition shadow-sm"
            >
              + New Job
            </button>
            <button
              onClick={logout}
              className="px-3 py-2 border border-gray-200 text-gray-500 text-sm rounded-xl hover:bg-gray-50 transition"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* ── Nav ─────────────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-gray-200 px-6">
        <div className="max-w-7xl mx-auto flex gap-1">
          {NAV.map((v) => (
            <button
              key={v.id}
              onClick={() => setActiveView(v.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeView === v.id
                  ? 'border-indigo-500 text-indigo-700'
                  : 'border-transparent text-gray-500 hover:text-gray-800'
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Content ─────────────────────────────────────────────────────── */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-5 md:p-6">

        {activeView === 'search' && (
          <SearchPanel onOpenProject={(id) => navigate(`/projects/${id}`)} />
        )}
        {activeView === 'queues' && (
          <OperationalQueuesPanel onOpenProject={(id) => navigate(`/projects/${id}`)} />
        )}
        {activeView === 'settings' && <TenantSettingsPanel />}

        {activeView === 'projects' && (
          loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
              {[1, 2, 3].map((i) => <div key={i} className="h-44 bg-gray-100 rounded-2xl" />)}
            </div>
          ) : projects.length === 0 ? (
            <EmptyState onCreate={openCreate} />
          ) : (
            <div className="space-y-8">
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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-xl font-black text-gray-900 mb-1">New Fabrication Job</h3>
            <p className="text-sm text-gray-500 mb-5">Fill in the job details — you can edit these later.</p>

            <div className="space-y-4">
              <Field label="Job / Project Name *" hint="e.g. Haven On Main Phase 2">
                <input
                  data-testid="create-project-name"
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && newName.trim() && handleCreate()}
                  placeholder="Haven On Main Phase 2"
                  autoFocus
                  className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                />
              </Field>
              <Field label="Builder / Client" hint="Who is this job for?">
                <input
                  data-testid="create-project-client"
                  type="text"
                  value={newClient}
                  onChange={(e) => setNewClient(e.target.value)}
                  placeholder="Meritage Homes"
                  className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                />
              </Field>
              <Field label="Material" hint="Stone type or colour">
                <input
                  data-testid="create-project-material"
                  type="text"
                  value={newMaterial}
                  onChange={(e) => setNewMaterial(e.target.value)}
                  placeholder="3CM Calacatta Gold Quartz"
                  className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                />
              </Field>
              <Field label="Site Address">
                <input
                  type="text"
                  value={newAddress}
                  onChange={(e) => setNewAddress(e.target.value)}
                  placeholder="1234 Main St, Phoenix AZ"
                  className="w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                />
              </Field>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2.5 border border-gray-200 text-gray-700 rounded-xl text-sm hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                data-testid="create-project-submit"
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl disabled:opacity-50 transition shadow-sm"
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
    <label className="flex items-baseline gap-2 text-xs font-bold text-gray-700 mb-1.5">
      {label}
      {hint && <span className="font-normal text-gray-400">{hint}</span>}
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
    <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">{title}</p>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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
      className="bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md hover:border-indigo-300 cursor-pointer transition-all p-5 group flex flex-col"
    >
      {/* Top row: status dot + status badge */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full shrink-0 mt-0.5 ${sc.dot}`} />
          <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full ${sc.cls}`}>{sc.label}</span>
        </div>
        <span className="text-xs text-gray-400">{relativeDate(project.created_at)}</span>
      </div>

      {/* Project name */}
      <h3 className="text-base font-black text-gray-900 group-hover:text-indigo-700 transition-colors leading-tight mb-2 truncate">
        {project.name}
      </h3>

      {/* Meta */}
      <div className="space-y-1 flex-1">
        {project.client_name && (
          <p className="text-sm text-gray-600">
            <span className="text-gray-400 text-xs mr-1">Builder</span>
            <span className="font-semibold">{project.client_name}</span>
          </p>
        )}
        {project.material && (
          <p className="text-sm text-gray-500 truncate">{project.material}</p>
        )}
        {project.address && (
          <p className="text-xs text-gray-400 truncate">{project.address}</p>
        )}
      </div>

      {/* Footer */}
      <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
        <span className="text-xs text-gray-400">
          {project.issue_date
            ? `Issue: ${new Date(project.issue_date).toLocaleDateString()}`
            : 'No issue date'}
        </span>
        <span className="text-xs text-indigo-500 font-bold opacity-0 group-hover:opacity-100 transition-opacity">
          Open →
        </span>
      </div>
    </div>
  );
};

const EmptyState: React.FC<{ onCreate: () => void }> = ({ onCreate }) => (
  <div className="bg-white rounded-2xl border border-dashed border-gray-300 p-16 text-center max-w-lg mx-auto">
    <div className="text-5xl mb-4">🏗</div>
    <h3 className="text-xl font-black text-gray-900 mb-2">No jobs yet</h3>
    <p className="text-gray-500 text-sm mb-6 max-w-xs mx-auto">
      Create your first fabrication job to start building unit schedules and generating shop drawing packages.
    </p>
    <button
      onClick={onCreate}
      className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl transition shadow-sm"
    >
      Create First Job →
    </button>
  </div>
);
