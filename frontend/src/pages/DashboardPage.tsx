import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import { Project, ProjectStatus } from '../types/hierarchy';
import { useAuthStore } from '../store/authStore';
import { OperationalQueuesPanel } from '../components/OperationalQueuesPanel';
import { SearchPanel } from '../components/SearchPanel';
import { TenantSettingsPanel } from '../components/TenantSettingsPanel';

export const DashboardPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState<'projects' | 'search' | 'queues' | 'settings'>('projects');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newClientName, setNewClientName] = useState('');
  const [newMaterial, setNewMaterial] = useState('');
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);

  const openCreateModal = () => {
    setNewProjectName('');
    setNewClientName('');
    setNewMaterial('');
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

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">BuildDesk Fabrication</h1>
          <p className="text-sm text-gray-500">Multifamily Package Generator</p>
        </div>
        <div className="flex items-center space-x-4">
          <button onClick={openCreateModal} className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700">
            + New Project
          </button>
          <button onClick={logout} className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50">
            Sign out
          </button>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-semibold text-gray-900">Operations</h2>
          <div className="flex gap-2">
            {(['projects', 'search', 'queues', 'settings'] as const).map((view) => (
              <button
                key={view}
                onClick={() => setActiveView(view)}
                className={`px-3 py-2 text-sm rounded-md border ${activeView === view ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300'}`}
              >
                {view[0].toUpperCase() + view.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {activeView === 'search' && <SearchPanel onOpenProject={(id) => navigate(`/projects/${id}`)} />}
        {activeView === 'queues' && <OperationalQueuesPanel onOpenProject={(id) => navigate(`/projects/${id}`)} />}
        {activeView === 'settings' && <TenantSettingsPanel />}
        {activeView === 'projects' && (
          loading ? (
            <p className="text-gray-500">Loading projects...</p>
          ) : projects.length === 0 ? (
            <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200 text-center">
              <h3 className="text-lg font-medium text-gray-900 mb-2">No projects found</h3>
              <p className="text-gray-500 mb-4">Create your first multifamily countertop project to get started.</p>
              <button onClick={openCreateModal} className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700">
                Create Project
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {projects.map((p) => (
                <div 
                  key={p.project_id} 
                  onClick={() => navigate(`/projects/${p.project_id}`)}
                  className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 cursor-pointer hover:border-blue-400 hover:shadow-md transition"
                >
                  <div className="flex justify-between items-start mb-4">
                    <h3 className="text-lg font-bold text-gray-900 truncate pr-2">{p.name}</h3>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${p.status === ProjectStatus.DRAFT ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}`}>
                      {p.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="space-y-2 text-sm text-gray-600">
                    <p><span className="font-medium">Client:</span> {p.client_name || '—'}</p>
                    <p><span className="font-medium">Material:</span> {p.material || '—'}</p>
                    <p><span className="font-medium">Updated:</span> {new Date(p.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
              ))}
            </div>
          )
        )}
      </main>

      {showCreateModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h3 className="text-lg font-bold mb-4">New Fabrication Project</h3>
            <label className="block text-xs font-bold text-gray-600 mb-1">Project Name</label>
            <input
              data-testid="create-project-name"
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="Haven On Main New"
              className="border w-full p-2 rounded mb-4"
            />
            <label className="block text-xs font-bold text-gray-600 mb-1">Client</label>
            <input
              data-testid="create-project-client"
              type="text"
              value={newClientName}
              onChange={(e) => setNewClientName(e.target.value)}
              placeholder="Virgin Surfaces"
              className="border w-full p-2 rounded mb-4"
            />
            <label className="block text-xs font-bold text-gray-600 mb-1">Material</label>
            <input
              data-testid="create-project-material"
              type="text"
              value={newMaterial}
              onChange={(e) => setNewMaterial(e.target.value)}
              placeholder="3CM Granite"
              className="border w-full p-2 rounded mb-6"
            />
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setShowCreateModal(false)} className="px-4 py-2 rounded border">
                Cancel
              </button>
              <button
                type="button"
                data-testid="create-project-submit"
                onClick={handleCreateProject}
                disabled={creating || !newProjectName.trim()}
                className="px-4 py-2 rounded bg-blue-600 text-white font-bold disabled:opacity-50"
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
