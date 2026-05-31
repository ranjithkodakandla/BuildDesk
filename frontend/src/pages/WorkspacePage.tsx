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

// Tabs ordered by workflow: the fabricator goes left-to-right through their job
const TABS: { id: WorkspaceTab; label: string; icon: string; hint: string }[] = [
  { id: 'overview',    icon: '⬛', label: 'Overview',       hint: 'Job status & checklist' },
  { id: 'units',       icon: '🏠', label: 'Units & Types',  hint: 'Unit schedule and type assignments' },
  { id: 'fabrication', icon: '📐', label: 'Shop Drawings',  hint: 'Assemblies and parts' },
  { id: 'package',     icon: '📄', label: 'PDF Package',    hint: 'Generate and download fabrication PDF' },
  { id: 'operations',  icon: '📋', label: 'Issues & RFIs',  hint: 'RFIs, approvals, search' },
];

const STATUS_CONFIG: Record<string, { label: string; cls: string; dot: string }> = {
  draft:       { label: 'Draft',       cls: 'bg-slate-100 text-slate-700',  dot: 'bg-slate-400' },
  in_progress: { label: 'In Progress', cls: 'bg-amber-100 text-amber-800',  dot: 'bg-amber-400' },
  issued:      { label: 'Issued',      cls: 'bg-green-100 text-green-800',  dot: 'bg-green-500' },
  archived:    { label: 'Archived',    cls: 'bg-gray-100 text-gray-500',    dot: 'bg-gray-400'  },
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
          <div className="w-10 h-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-sm text-gray-500 font-medium">Loading project…</p>
        </div>
      </div>
    );
  }

  const sc = STATUS_CONFIG[project.status] || STATUS_CONFIG['draft'];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200 px-6 py-0">
        <div className="flex items-center justify-between h-14">

          {/* Left: breadcrumb + project name */}
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => navigate('/dashboard')}
              className="shrink-0 text-gray-400 hover:text-indigo-600 text-sm font-medium flex items-center gap-1 transition-colors"
            >
              ← All Projects
            </button>
            <span className="text-gray-200 shrink-0">|</span>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-gray-900 truncate">{project.name}</h1>
                <span className={`shrink-0 px-2 py-0.5 text-xs font-bold rounded-full ${sc.cls}`}>
                  {sc.label}
                </span>
              </div>
              <p className="text-xs text-gray-400 truncate hidden sm:block">
                {[project.client_name, project.material, project.address].filter(Boolean).join(' · ')}
              </p>
            </div>
          </div>

          {/* Right: actions */}
          <div className="flex items-center gap-2 shrink-0 ml-4">
            <button
              onClick={() => setShowExportModal(true)}
              className="hidden sm:flex px-3 py-1.5 border border-gray-300 text-gray-600 text-sm font-medium rounded-lg hover:bg-gray-50 transition items-center gap-1"
            >
              Export
            </button>
            <button
              onClick={() => setActiveTab('package')}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-lg shadow-sm transition"
            >
              Generate PDF
            </button>
          </div>
        </div>
      </header>

      {/* ── Tab bar ─────────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-gray-200 px-4">
        <nav className="flex gap-0 overflow-x-auto">
          {TABS.map((tab, idx) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              title={tab.hint}
              className={`
                relative flex items-center gap-1.5 px-4 py-3.5 text-sm font-medium whitespace-nowrap
                border-b-2 transition-colors
                ${activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-700 bg-indigo-50/50'
                  : 'border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300'
                }
              `}
            >
              {/* Step number pill — shows workflow order */}
              <span className={`
                w-5 h-5 rounded-full text-xs font-black flex items-center justify-center shrink-0
                ${activeTab === tab.id ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-500'}
              `}>
                {idx + 1}
              </span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-auto p-5 md:p-6">
        {activeTab === 'overview' && (
          <OverviewPanel project={project} onNavigate={setActiveTab} />
        )}
        {activeTab === 'units' && (
          <HierarchyPanel project={project} />
        )}
        {activeTab === 'fabrication' && (
          <AssembliesPanel project={project} />
        )}
        {activeTab === 'package' && (
          <PackagesPanel project={project} />
        )}
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
