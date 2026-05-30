import React, { useEffect, useState } from 'react';
import { Project } from '../types/hierarchy';
import { ProjectPackage, ProjectPackageStatus } from '../types/packages';
import { assembliesApi } from '../api/assemblies';
import { packagesApi } from '../api/packages';
import { projectsApi } from '../api/projects';

interface Props {
  project: Project;
  onNavigate: (tab: 'units' | 'fabrication' | 'package' | 'operations') => void;
}

export const OverviewPanel: React.FC<Props> = ({ project, onNavigate }) => {
  const [unitCount, setUnitCount] = useState(0);
  const [assemblyCount, setAssemblyCount] = useState(0);
  const [pkg, setPkg] = useState<ProjectPackage | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [units, assemblies, status] = await Promise.all([
          projectsApi.listUnits(project.project_id).catch(() => []),
          assembliesApi.listAssemblies(project.project_id).catch(() => []),
          packagesApi.getPackageStatus(project.project_id).catch(() => null),
        ]);
        setUnitCount(Array.isArray(units) ? units.length : 0);
        setAssemblyCount(Array.isArray(assemblies) ? assemblies.length : 0);
        setPkg(status);
      } catch {
        /* overview is best-effort */
      }
    };
    load();
  }, [project.project_id]);

  const cards = [
    { label: 'Units', value: String(unitCount), tab: 'units' as const },
    { label: 'Assemblies', value: String(assemblyCount), tab: 'fabrication' as const },
    {
      label: 'Latest Package',
      value: pkg?.status === ProjectPackageStatus.READY ? `Rev ${pkg.version}` : pkg?.status || 'None',
      tab: 'package' as const,
    },
    { label: 'Pending RFIs', value: '0', tab: 'operations' as const },
    { label: 'Approval', value: project.status.replace('_', ' ').toUpperCase(), tab: 'package' as const },
  ];

  return (
    <div className="space-y-6">
      <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-bold text-gray-900 mb-1">Project Overview</h2>
        <p className="text-sm text-gray-500 mb-6">
          {project.material || 'Material TBD'} | {project.client_name || 'No client'}
        </p>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {cards.map((c) => (
            <button
              key={c.label}
              type="button"
              onClick={() => onNavigate(c.tab)}
              className="text-left p-4 rounded-lg border border-gray-100 bg-gray-50 hover:bg-indigo-50 hover:border-indigo-200 transition"
            >
              <p className="text-xs uppercase tracking-wide text-gray-500">{c.label}</p>
              <p className="text-xl font-bold text-gray-900 mt-1">{c.value}</p>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
};
