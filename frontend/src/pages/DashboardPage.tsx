import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import { Project, ProjectStatus } from '../types/hierarchy';
import { useAuthStore } from '../store/authStore';

export const DashboardPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);

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

  const handleCreateProject = async () => {
    try {
      const newProj = await projectsApi.createProject({
        name: 'New Fabrication Project',
        status: ProjectStatus.DRAFT,
        hierarchy_config: { has_buildings: false, has_floors: false, has_unit_types: true },
      });
      navigate(`/projects/${newProj.project_id}`);
    } catch (err) {
      console.error('Failed to create project', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">BuildDesk Fabrication</h1>
          <p className="text-sm text-gray-500">Multifamily Package Generator</p>
        </div>
        <div className="flex items-center space-x-4">
          <button onClick={handleCreateProject} className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700">
            + New Project
          </button>
          <button onClick={logout} className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50">
            Sign out
          </button>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        <h2 className="text-2xl font-semibold text-gray-900 mb-6">Active Projects</h2>
        {loading ? (
          <p className="text-gray-500">Loading projects...</p>
        ) : projects.length === 0 ? (
          <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200 text-center">
            <h3 className="text-lg font-medium text-gray-900 mb-2">No projects found</h3>
            <p className="text-gray-500 mb-4">Create your first multifamily countertop project to get started.</p>
            <button onClick={handleCreateProject} className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700">
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
        )}
      </main>
    </div>
  );
};
