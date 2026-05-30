import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import { Project } from '../types/hierarchy';
import { HierarchyPanel } from '../components/HierarchyPanel';
import { AssembliesPanel } from '../components/AssembliesPanel';
import { PackagesPanel } from '../components/PackagesPanel';
import { OverviewPanel } from '../components/OverviewPanel';
import ExportModal from '../components/ExportModal';
import { SearchPanel } from '../components/SearchPanel';
import { OperationalQueuesPanel } from '../components/OperationalQueuesPanel';

type WorkspaceTab = 'overview' | 'units' | 'fabrication' | 'package' | 'operations';

const TABS: { id: WorkspaceTab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'units', label: 'Units' },
  { id: 'fabrication', label: 'Fabrication' },
  { id: 'package', label: 'Package' },
  { id: 'operations', label: 'Operations' },
];

export const WorkspacePage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('overview');
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
            <p className="text-sm text-gray-500">
              {project.client_name || 'No Client'} · {project.status.toUpperCase()}
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowExportModal(true)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm"
        >
          Export Data
        </button>
      </header>

      <div className="bg-white border-b border-gray-200 px-6">
        <nav className="flex space-x-8">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <main className="flex-1 overflow-auto p-6">
        {activeTab === 'overview' && (
          <OverviewPanel project={project} onNavigate={setActiveTab} />
        )}
        {activeTab === 'units' && <HierarchyPanel project={project} />}
        {activeTab === 'fabrication' && <AssembliesPanel project={project} />}
        {activeTab === 'package' && <PackagesPanel project={project} />}
        {activeTab === 'operations' && (
          <div className="space-y-6">
            <SearchPanel projectId={project.project_id} />
            <OperationalQueuesPanel onOpenProject={(id) => navigate(`/projects/${id}`)} />
          </div>
        )}
      </main>

      {showExportModal && (
        <ExportModal projectId={project.project_id} onClose={() => setShowExportModal(false)} />
      )}
    </div>
  );
};
