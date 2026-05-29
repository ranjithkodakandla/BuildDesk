import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import { Project } from '../types/hierarchy';
import { useAuthStore } from '../store/authStore';
import { HierarchyPanel } from '../components/HierarchyPanel';
import { AssembliesPanel } from '../components/AssembliesPanel';
import { PackagesPanel } from '../components/PackagesPanel';
import ExportModal from '../components/ExportModal';

export const WorkspacePage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [activeTab, setActiveTab] = useState<'hierarchy' | 'assemblies' | 'packages'>('assemblies');
  const [showExportModal, setShowExportModal] = useState(false);

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
        <div className="flex items-center space-x-3">
          <button 
            onClick={() => setShowExportModal(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
          >
            Export Data
          </button>
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
      
      {showExportModal && (
        <ExportModal 
          projectId={project.project_id} 
          onClose={() => setShowExportModal(false)} 
        />
      )}
    </div>
  );
};
