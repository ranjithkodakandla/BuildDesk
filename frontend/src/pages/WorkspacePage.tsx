import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import { Project, ProjectStatus } from '../types/hierarchy';
import { HierarchyPanel } from '../components/HierarchyPanel';
import { AssembliesPanel } from '../components/AssembliesPanel';
import { PackagesPanel } from '../components/PackagesPanel';
import { OverviewPanel } from '../components/OverviewPanel';
import ExportModal from '../components/ExportModal';
import { SearchPanel } from '../components/SearchPanel';
import { OperationalQueuesPanel } from '../components/OperationalQueuesPanel';

type WorkspaceTab = 'overview' | 'units' | 'fabrication' | 'package' | 'operations';

const TABS: { id: WorkspaceTab; label: string; hint: string }[] = [
  { id: 'overview',    label: 'Home',           hint: 'Project command center' },
  { id: 'units',       label: 'Unit Schedule',  hint: 'Units and type assignments' },
  { id: 'fabrication', label: 'Shop Drawings',  hint: 'Assemblies and parts' },
  { id: 'package',     label: 'Package',        hint: 'Generate and download PDF' },
  { id: 'operations',  label: 'Queue',          hint: 'RFIs, approvals, search' },
];

const STATUS_COLORS: Record<string, string> = {
  draft:       'bg-slate-100 text-slate-700',
  in_progress: 'bg-amber-100 text-amber-800',
  issued:      'bg-green-100 text-green-800',
  archived:    'bg-gray-100 text-gray-500',
};

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

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading workspace…</p>
        </div>
      </div>
    );
  }

  const statusLabel = project.status.replace('_', ' ').toUpperCase();
  const statusClass = STATUS_COLORS[project.status] || 'bg-gray-100 text-gray-600';

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="text-gray-400 hover:text-gray-700 text-sm font-medium flex items-center gap-1 transition-colors"
            >
              ← Projects
            </button>
            <div className="h-5 w-px bg-gray-200" />
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-lg font-bold text-gray-900 tracking-tight">{project.name}</h1>
                <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${statusClass}`}>
                  {statusLabel}
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                {project.client_name || 'No client'}
                {project.material ? ` · ${project.material}` : ''}
                {project.address ? ` · ${project.address}` : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowExportModal(true)}
              className="px-3 py-1.5 border border-gray-300 text-gray-600 text-sm font-medium rounded-lg hover:bg-gray-50 transition"
            >
              Export
            </button>
            <button
              onClick={() => setActiveTab('package')}
              className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm transition"
            >
              Generate Package
            </button>
          </div>
        </div>
      </header>

      {/* Tab bar */}
      <div className="bg-white border-b border-gray-200 px-6">
        <nav className="flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              title={tab.hint}
              className={`py-3 px-3 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Main content */}
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
