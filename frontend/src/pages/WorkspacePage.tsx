import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import { Project } from '../types/hierarchy';
import { useAuthStore } from '../store/authStore';

export const WorkspacePage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [activeTab, setActiveTab] = useState<'hierarchy' | 'assemblies' | 'packages'>('assemblies');

  useEffect(() => {
    if (projectId) {
      projectsApi.getProject(projectId).then(setProject).catch(console.error);
    }
  }, [projectId]);

  if (!project) return <div className="p-8 text-center text-gray-500">Loading project workspace...</div>;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button onClick={() => navigate('/dashboard')} className="text-gray-500 hover:text-gray-700">
            ← Back
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">{project.name}</h1>
            <p className="text-sm text-gray-500">{project.client_name || 'No Client'} • {project.status.toUpperCase()}</p>
          </div>
        </div>
      </header>

      <div className="bg-white border-b border-gray-200 px-6">
        <nav className="flex space-x-8">
          {(['hierarchy', 'assemblies', 'packages'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${activeTab === tab ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}
            >
              {tab.replace('_', ' ')}
            </button>
          ))}
        </nav>
      </div>

      <main className="flex-1 overflow-auto p-6">
        {activeTab === 'hierarchy' && <HierarchyPanel project={project} />}
        {activeTab === 'assemblies' && <AssembliesPanel project={project} />}
        {activeTab === 'packages' && <PackagesPanel project={project} />}
      </main>
    </div>
  );
};

// --- Subpanels (Stubs for now, will implement full later) ---

const HierarchyPanel = ({ project }: { project: Project }) => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <h2 className="text-lg font-bold mb-4">Project Hierarchy & Units</h2>
      <p className="text-sm text-gray-600">Configure buildings, floors, unit types (A1, A1-MIR, B1), and individual units here.</p>
    </div>
  );
};

const AssembliesPanel = ({ project }: { project: Project }) => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <h2 className="text-lg font-bold mb-4">Fabrication Assemblies</h2>
      <p className="text-sm text-gray-600">Define Kitchens, Vanities, Islands with edges, cutouts, holes, and splashes.</p>
    </div>
  );
};

const PackagesPanel = ({ project }: { project: Project }) => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <h2 className="text-lg font-bold mb-4">Package Generation</h2>
      <p className="text-sm text-gray-600">Generate the multi-page PDF fabrication package.</p>
    </div>
  );
};
