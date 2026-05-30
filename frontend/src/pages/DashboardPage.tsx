import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import { Project, ProjectStatus } from '../types/hierarchy';
import { useAuthStore } from '../store/authStore';
import { OperationalQueuesPanel } from '../components/OperationalQueuesPanel';
import { SearchPanel } from '../components/SearchPanel';
import { TenantSettingsPanel } from '../components/TenantSettingsPanel';

type DashboardView = 'projects' | 'search' | 'queues' | 'settings';

const STATUS_CONFIG: Record<string, { label: string; cls: string }> = {
  draft:       { label: 'Draft',       cls: 'bg-slate-100 text-slate-600' },
  in_progress: { label: 'In Progress', cls: 'bg-amber-100 text-amber-700' },
  issued:      { label: 'Issued',      cls: 'bg-green-100 text-green-700' },
  archived:    { label: 'Archived',    cls: 'bg-gray-100 text-gray-500' },
};

function relativeDate(isoStr: string): string {
  const now = Date.now();
  const then = new Date(isoStr).getTime();
  const days = Math.floor((now - then) / 86_400_000);
  if (days === 0) return 'Today';
  if (days === 1) return '1 day ago';
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return months === 1 ? '1 month ago' : `${months} months ago`;
}

export const DashboardPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState<DashboardView>('projects');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newClientName, setNewClientName] = useState('');
  const [newMaterial, setNewMaterial] = useState('');
  const [newAddress, setNewAddress] = useState('');
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  const { logout, user } = useAuthStore();

  const openCreateModal = () => {
    setNewProjectName('');
    setNewClientName('');
    setNewMaterial('');
    setNewAddress('');
    setShowCreateModal(true);
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;
    setCreating(true);
    try {
      const newProj = await projectsApi.createProject({
        name: newProjectName.trim(),
        client_name: newClientName.trim() || undefined,
        material: newMaterial.trim() || undefined,
        address: newAddress.trim() || undefined,
        status: ProjectStatus.DRAFT,
        hierarchy_config: { has_buildings: false, has_floors: false, has_unit_types: true },
      });
      setShowCreateModal(false);
      navigate(`/projects/${newProj.project_id}`);
    } catch (err) {
      console.error('Failed to create project', err);
    } finally {
      setCreating(false);
    }
  };

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const data = await projectsApi.listProjects();
        setProjects(data);
      } catch (err) {
        console.error('Failed to load projects', err);
      } finally {
        setLoading(false);
      }
    };
    fetchProjects();
  }, []);

  const NAV_VIEWS: { id: DashboardView; label: string }[] = [
    { id: 'projects', label: 'Projects' },
    { id: 'queues',   label: 'Queue' },
    { id: 'search',   label: 'Search' },
    { id: 'settings', label: 'Settings' },
  ];

  // Group projects by status
  const activeProjects = projects.filter(
    (p) => p.status === ProjectStatus.IN_PROGRESS || p.status === ProjectStatus.DRAFT
  );
  const issuedProjects = projects.filter((p) => p.status === ProjectStatus.ISSUED);
  const archivedProjects = projects.filter((p) => p.status === ProjectStatus.ARCHIVED);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-600 to-indigo-700 flex items-center justify-center shadow-sm">
            <span className="text-white font-black text-sm">B</span>
          </div>
          <div>
            <h1 className="text-base font-bold text-gray-900 tracking-tight">BuildDesk</h1>
            <p className="text-xs text-gray-400">Multifamily Countertop Fabrication</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {user?.email && <span className="text-xs text-gray-400 hidden md:block">{user.email}</span>}
          <button
            onClick={openCreateModal}
            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
          >
            + New Project
          </button>
          <button
            onClick={logout}
            className="px-3 py-1.5 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {/* Nav tabs */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex gap-1">
            {NAV_VIEWS.map((v) => (
              <button
                key={v.id}
                onClick={() => setActiveView(v.id)}
                className={`px-4 py-2 text-sm rounded-lg font-medium transition ${
                  activeView === v.id
                    ? 'bg-indigo-600 text-white'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {v.label}
              </button>
            ))}
          </div>
          {activeView === 'projects' && !loading && (
            <p className="text-sm text-gray-400">{projects.length} project{projects.length !== 1 ? 's' : ''}</p>
          )}
        </div>

        {/* Views */}
        {activeView === 'search' && (
          <SearchPanel onOpenProject={(id) => navigate(`/projects/${id}`)} />
        )}
        {activeView === 'queues' && (
          <OperationalQueuesPanel onOpenProject={(id) => navigate(`/projects/${id}`)} />
        )}
        {activeView === 'settings' && <TenantSettingsPanel />}

        {activeView === 'projects' && (
          loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 animate-pulse">
              {[1,2,3].map(i => <div key={i} className="h-40 bg-gray-100 rounded-xl" />)}
            </div>
          ) : projects.length === 0 ? (
            <div className="bg-white rounded-xl border border-dashed border-gray-300 p-16 text-center">
              <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🏗</span>
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">No projects yet</h3>
              <p className="text-gray-500 mb-5 text-sm max-w-xs mx-auto">
                Create your first multifamily countertop project to begin generating fabrication packages.
              </p>
              <button
                onClick={openCreateModal}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition"
              >
                Create First Project
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Active projects */}
              {activeProjects.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Active</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {activeProjects.map((p) => (
                      <ProjectCard key={p.project_id} project={p} onClick={() => navigate(`/projects/${p.project_id}`)} />
                    ))}
                  </div>
                </div>
              )}

              {/* Issued projects */}
              {issuedProjects.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Issued</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {issuedProjects.map((p) => (
                      <ProjectCard key={p.project_id} project={p} onClick={() => navigate(`/projects/${p.project_id}`)} />
                    ))}
                  </div>
                </div>
              )}

              {/* Archived projects */}
              {archivedProjects.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Archived</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {archivedProjects.map((p) => (
                      <ProjectCard key={p.project_id} project={p} onClick={() => navigate(`/projects/${p.project_id}`)} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        )}
      </main>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-lg font-bold text-gray-900 mb-1">New Fabrication Project</h3>
            <p className="text-sm text-gray-500 mb-5">Enter the project details to get started.</p>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-600 mb-1">Project Name *</label>
                <input
                  data-testid="create-project-name"
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="Haven On Main Phase 2"
                  className="border border-gray-300 w-full p-2.5 rounded-lg text-sm"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-600 mb-1">Client / Builder</label>
                <input
                  data-testid="create-project-client"
                  type="text"
                  value={newClientName}
                  onChange={(e) => setNewClientName(e.target.value)}
                  placeholder="Virgin Surfaces"
                  className="border border-gray-300 w-full p-2.5 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-600 mb-1">Material</label>
                <input
                  data-testid="create-project-material"
                  type="text"
                  value={newMaterial}
                  onChange={(e) => setNewMaterial(e.target.value)}
                  placeholder="3CM Quartz — Calacatta Gold"
                  className="border border-gray-300 w-full p-2.5 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-600 mb-1">Project Address</label>
                <input
                  type="text"
                  value={newAddress}
                  onChange={(e) => setNewAddress(e.target.value)}
                  placeholder="1234 Main St, Phoenix, AZ"
                  className="border border-gray-300 w-full p-2.5 rounded-lg text-sm"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                data-testid="create-project-submit"
                onClick={handleCreateProject}
                disabled={creating || !newProjectName.trim()}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg disabled:opacity-50 transition"
              >
                {creating ? 'Creating…' : 'Create Project'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// --- Project Card ---
const ProjectCard: React.FC<{ project: Project; onClick: () => void }> = ({ project, onClick }) => {
  const sc = STATUS_CONFIG[project.status] || { label: project.status, cls: 'bg-gray-100 text-gray-600' };

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md hover:border-indigo-300 cursor-pointer transition-all p-5 group"
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-base font-bold text-gray-900 truncate pr-2 group-hover:text-indigo-700 transition-colors">
          {project.name}
        </h3>
        <span className={`px-2 py-0.5 text-xs font-semibold rounded-full shrink-0 ${sc.cls}`}>
          {sc.label}
        </span>
      </div>

      <div className="space-y-1 text-sm text-gray-600">
        {project.client_name && (
          <p className="flex items-center gap-1.5">
            <span className="text-gray-400 text-xs">Client</span>
            <span className="font-medium text-gray-700">{project.client_name}</span>
          </p>
        )}
        {project.material && (
          <p className="flex items-center gap-1.5">
            <span className="text-gray-400 text-xs">Material</span>
            <span className="text-gray-600">{project.material}</span>
          </p>
        )}
        {project.address && (
          <p className="flex items-center gap-1.5">
            <span className="text-gray-400 text-xs">Address</span>
            <span className="text-gray-500 truncate">{project.address}</span>
          </p>
        )}
      </div>

      <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
        <span>{relativeDate(project.created_at)}</span>
        <span className="text-indigo-500 opacity-0 group-hover:opacity-100 transition-opacity font-medium">
          Open →
        </span>
      </div>
    </div>
  );
};
