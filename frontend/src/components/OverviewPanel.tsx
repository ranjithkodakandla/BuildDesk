import React, { useEffect, useState } from 'react';
import { Project, ProjectStatus, UnitType, Unit } from '../types/hierarchy';
import { ProjectPackage, ProjectPackageStatus } from '../types/packages';
import { Assembly } from '../types/fabrication';
import { assembliesApi } from '../api/assemblies';
import { packagesApi } from '../api/packages';
import { projectsApi } from '../api/projects';

interface Props {
  project: Project;
  onNavigate: (tab: 'units' | 'fabrication' | 'package' | 'operations') => void;
}

type HealthState = 'ok' | 'warn' | 'none' | 'error';

interface HealthTile {
  label: string;
  state: HealthState;
  primary: string;
  secondary: string;
  tab: 'units' | 'fabrication' | 'package' | 'operations';
}

const stateColor: Record<HealthState, string> = {
  ok:    'border-green-200 bg-green-50',
  warn:  'border-amber-200 bg-amber-50',
  none:  'border-gray-200 bg-gray-50',
  error: 'border-red-200 bg-red-50',
};

const stateDot: Record<HealthState, string> = {
  ok:    'bg-green-500',
  warn:  'bg-amber-400',
  none:  'bg-gray-300',
  error: 'bg-red-500',
};

const stateLabel: Record<HealthState, string> = {
  ok:    'Ready',
  warn:  'Needs Attention',
  none:  'Not Started',
  error: 'Blocked',
};

export const OverviewPanel: React.FC<Props> = ({ project, onNavigate }) => {
  const [unitTypes, setUnitTypes] = useState<UnitType[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [assemblies, setAssemblies] = useState<Assembly[]>([]);
  const [pkg, setPkg] = useState<ProjectPackage | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [ut, u, asm, pkgStatus] = await Promise.all([
          projectsApi.listUnitTypes(project.project_id).catch(() => [] as UnitType[]),
          projectsApi.listUnits(project.project_id).catch(() => [] as Unit[]),
          assembliesApi.listAssemblies(project.project_id).catch(() => [] as Assembly[]),
          packagesApi.getPackageStatus(project.project_id).catch(() => null),
        ]);
        setUnitTypes(ut);
        setUnits(u);
        setAssemblies(asm);
        setPkg(pkgStatus);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [project.project_id]);

  // --- Health computation ---
  const untypedUnits = units.filter((u) => !u.unit_type_id).length;
  const emptyAssemblies = assemblies.filter((a) => !a.parts || a.parts.length === 0).length;

  const importState: HealthState =
    units.length === 0 ? 'none' :
    untypedUnits > 0 ? 'warn' : 'ok';

  const fabricationState: HealthState =
    assemblies.length === 0 ? 'none' :
    emptyAssemblies > 0 ? 'warn' : 'ok';

  const packageState: HealthState =
    pkg === null ? 'none' :
    pkg.status === ProjectPackageStatus.READY ? 'ok' :
    pkg.status === ProjectPackageStatus.GENERATING ? 'warn' : 'none';

  const approvalState: HealthState =
    project.status === ProjectStatus.ISSUED ? 'ok' :
    project.status === ProjectStatus.IN_PROGRESS ? 'warn' :
    project.status === ProjectStatus.DRAFT ? 'none' : 'none';

  const tiles: HealthTile[] = [
    {
      label: 'Import / Schedule',
      state: importState,
      primary: units.length === 0 ? 'No units' : `${units.length} units`,
      secondary: units.length === 0
        ? 'Import your unit schedule'
        : `${unitTypes.length} types · ${untypedUnits > 0 ? `${untypedUnits} unassigned` : 'All typed'}`,
      tab: 'units',
    },
    {
      label: 'Fabrication',
      state: fabricationState,
      primary: assemblies.length === 0 ? 'No assemblies' : `${assemblies.length} assemblies`,
      secondary: assemblies.length === 0
        ? 'Create shop drawings'
        : `${assemblies.reduce((n, a) => n + (a.parts?.length || 0), 0)} parts · ${emptyAssemblies > 0 ? `${emptyAssemblies} empty` : 'All have parts'}`,
      tab: 'fabrication',
    },
    {
      label: 'Package',
      state: packageState,
      primary: pkg === null ? 'Not generated' : `${pkg.version}`,
      secondary: pkg === null
        ? 'Generate first package'
        : pkg.status === ProjectPackageStatus.GENERATING
          ? 'Generating…'
          : `${pkg.page_count ?? '—'} pages · ${pkg.generated_at ? new Date(pkg.generated_at).toLocaleDateString() : ''}`,
      tab: 'package',
    },
    {
      label: 'Approval Status',
      state: approvalState,
      primary: project.status.replace('_', ' ').toUpperCase(),
      secondary: project.status === ProjectStatus.ISSUED
        ? 'Package issued to client'
        : project.status === ProjectStatus.IN_PROGRESS
          ? 'Fabrication in progress'
          : 'Project in draft',
      tab: 'package',
    },
  ];

  // --- Warnings ---
  const warnings: string[] = [];
  if (units.length === 0) warnings.push('No units imported — import your unit schedule to begin.');
  else if (untypedUnits > 0) warnings.push(`${untypedUnits} unit${untypedUnits > 1 ? 's' : ''} have no type assignment.`);
  if (unitTypes.length === 0 && units.length > 0) warnings.push('No unit types defined — units cannot be grouped for fabrication.');
  if (assemblies.length === 0) warnings.push('No shop drawings created — fabrication package will be empty.');
  else if (emptyAssemblies > 0) warnings.push(`${emptyAssemblies} assembl${emptyAssemblies > 1 ? 'ies' : 'y'} have no parts defined.`);
  if (pkg === null) warnings.push('No fabrication package generated yet.');

  const pkgReady = pkg?.status === ProjectPackageStatus.READY;

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-24 bg-gray-100 rounded-xl" />
        <div className="grid grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-28 bg-gray-100 rounded-xl" />)}
        </div>
        <div className="h-32 bg-gray-100 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-6xl">

      {/* Project vitals bar */}
      <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Project Command Center</p>
            <h2 className="text-2xl font-bold text-gray-900 mb-0.5">{project.name}</h2>
            <p className="text-sm text-gray-500">
              {project.client_name && <span className="font-medium text-gray-700">{project.client_name}</span>}
              {project.material && <span> · {project.material}</span>}
              {project.address && <span> · {project.address}</span>}
              {project.issue_date && (
                <span> · Issue date: {new Date(project.issue_date).toLocaleDateString()}</span>
              )}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-400 mb-1">Project health</p>
            <div className="flex items-center gap-2 justify-end">
              {tiles.map((t) => (
                <span key={t.label} className={`w-2.5 h-2.5 rounded-full ${stateDot[t.state]}`} title={`${t.label}: ${stateLabel[t.state]}`} />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Health tiles */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {tiles.map((tile) => (
          <button
            key={tile.label}
            type="button"
            onClick={() => onNavigate(tile.tab)}
            className={`text-left p-4 rounded-xl border-2 transition-all hover:shadow-md ${stateColor[tile.state]}`}
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wide">{tile.label}</p>
              <span className={`w-2 h-2 rounded-full ${stateDot[tile.state]}`} />
            </div>
            <p className="text-lg font-bold text-gray-900 leading-tight">{tile.primary}</p>
            <p className="text-xs text-gray-500 mt-1">{tile.secondary}</p>
          </button>
        ))}
      </div>

      {/* Quick actions + warnings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Quick actions */}
        <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Quick Actions</p>
          <div className="space-y-2">
            <button
              onClick={() => onNavigate('units')}
              className="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 transition text-sm font-medium text-gray-700 flex items-center justify-between group"
            >
              <span>Import / Review Unit Schedule</span>
              <span className="text-gray-400 group-hover:text-indigo-500 transition">→</span>
            </button>
            <button
              onClick={() => onNavigate('fabrication')}
              className="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 transition text-sm font-medium text-gray-700 flex items-center justify-between group"
            >
              <span>Review Shop Drawings</span>
              <span className="text-gray-400 group-hover:text-indigo-500 transition">→</span>
            </button>
            <button
              onClick={() => onNavigate('package')}
              className="w-full text-left px-4 py-3 rounded-lg border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 transition text-sm font-bold text-indigo-700 flex items-center justify-between group"
            >
              <span>Generate Fabrication Package</span>
              <span className="text-indigo-400 group-hover:text-indigo-600 transition">→</span>
            </button>
            {pkgReady && (
              <button
                onClick={() => onNavigate('package')}
                className="w-full text-left px-4 py-3 rounded-lg border border-green-200 bg-green-50 hover:bg-green-100 transition text-sm font-bold text-green-700 flex items-center justify-between group"
              >
                <span>Download Latest PDF</span>
                <span className="text-green-500">↓</span>
              </button>
            )}
            <button
              onClick={() => onNavigate('operations')}
              className="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 transition text-sm font-medium text-gray-700 flex items-center justify-between group"
            >
              <span>View Operational Queue</span>
              <span className="text-gray-400 group-hover:text-indigo-500 transition">→</span>
            </button>
          </div>
        </section>

        {/* Warnings */}
        <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
            {warnings.length > 0 ? `${warnings.length} Issue${warnings.length > 1 ? 's' : ''} Require Attention` : 'Project Status'}
          </p>

          {warnings.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-6 text-center">
              <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center mb-3">
                <span className="text-green-600 font-bold text-lg">✓</span>
              </div>
              <p className="text-sm font-medium text-green-700">All systems ready</p>
              <p className="text-xs text-gray-400 mt-1">No outstanding issues detected</p>
            </div>
          ) : (
            <ul className="space-y-2">
              {warnings.map((w, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-0.5 w-4 h-4 rounded-full bg-amber-100 flex items-center justify-center shrink-0">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                  </span>
                  <span className="text-gray-700">{w}</span>
                </li>
              ))}
            </ul>
          )}

          {/* Key stats */}
          <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-xl font-bold text-gray-900">{units.length}</p>
              <p className="text-xs text-gray-500">Units</p>
            </div>
            <div>
              <p className="text-xl font-bold text-gray-900">{assemblies.length}</p>
              <p className="text-xs text-gray-500">Assemblies</p>
            </div>
            <div>
              <p className="text-xl font-bold text-gray-900">
                {assemblies.reduce((n, a) => n + (a.parts?.length || 0), 0)}
              </p>
              <p className="text-xs text-gray-500">Parts</p>
            </div>
          </div>
        </section>
      </div>

    </div>
  );
};
