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

type StepState = 'done' | 'warn' | 'todo' | 'blocked';

interface WorkflowStep {
  num: number;
  title: string;
  state: StepState;
  summary: string;
  action?: string;
  tab: 'units' | 'fabrication' | 'package' | 'operations';
}

const stepColors: Record<StepState, { ring: string; bg: string; num: string; badge: string; text: string }> = {
  done:    { ring: 'border-green-300',  bg: 'bg-green-50',  num: 'bg-green-500 text-white',       badge: 'bg-green-100 text-green-800',  text: 'text-green-700'  },
  warn:    { ring: 'border-amber-300',  bg: 'bg-amber-50',  num: 'bg-amber-400 text-white',        badge: 'bg-amber-100 text-amber-800',  text: 'text-amber-700'  },
  todo:    { ring: 'border-gray-200',   bg: 'bg-white',     num: 'bg-gray-200 text-gray-600',      badge: 'bg-gray-100 text-gray-600',    text: 'text-gray-500'   },
  blocked: { ring: 'border-red-200',    bg: 'bg-red-50',    num: 'bg-red-400 text-white',          badge: 'bg-red-100 text-red-700',      text: 'text-red-600'    },
};

const stepLabel: Record<StepState, string> = {
  done:    'Done',
  warn:    'Action needed',
  todo:    'Not started',
  blocked: 'Blocked',
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

  // ── Step states ────────────────────────────────────────────────────────────
  const untypedCount  = units.filter((u) => !u.unit_type_id).length;
  const emptyAsmCount = assemblies.filter((a) => !a.parts || a.parts.length === 0).length;
  const totalParts    = assemblies.reduce((n, a) => n + (a.parts?.length || 0), 0);

  const step1State: StepState =
    units.length === 0   ? 'todo' :
    untypedCount > 0     ? 'warn' : 'done';

  const step2State: StepState =
    assemblies.length === 0 ? 'todo' :
    emptyAsmCount > 0       ? 'warn' : 'done';

  const step3State: StepState =
    pkg === null                                     ? 'todo' :
    pkg.status === ProjectPackageStatus.READY        ? 'done' :
    pkg.status === ProjectPackageStatus.GENERATING   ? 'warn' :
    pkg.status === ProjectPackageStatus.GENERATION_FAILED ? 'blocked' : 'todo';

  const allReady =
    step1State === 'done' &&
    step2State === 'done' &&
    step3State !== 'blocked';

  const steps: WorkflowStep[] = [
    {
      num: 1,
      title: 'Import & Assign Units',
      state: step1State,
      summary:
        units.length === 0
          ? 'No units yet — import your unit schedule'
          : untypedCount > 0
            ? `${units.length} units loaded · ${untypedCount} still need a type assigned`
            : `${units.length} units · ${unitTypes.length} types · All assigned`,
      action: step1State !== 'done' ? (units.length === 0 ? 'Import Units' : 'Assign Types') : undefined,
      tab: 'units',
    },
    {
      num: 2,
      title: 'Review Shop Drawings',
      state: step2State,
      summary:
        assemblies.length === 0
          ? 'No assemblies yet — create shop drawings for each unit type'
          : emptyAsmCount > 0
            ? `${assemblies.length} assemblies · ${emptyAsmCount} have no parts — add dimensions`
            : `${assemblies.length} assemblies · ${totalParts} parts · All complete`,
      action: step2State !== 'done' ? 'Review Drawings' : undefined,
      tab: 'fabrication',
    },
    {
      num: 3,
      title: 'Generate PDF Package',
      state: step3State,
      summary:
        pkg === null
          ? 'No PDF generated yet'
          : pkg.status === ProjectPackageStatus.GENERATING
            ? 'PDF is being generated — check back in a moment'
            : pkg.status === ProjectPackageStatus.READY
              ? `${pkg.version} · ${pkg.page_count ?? '—'} pages · ${pkg.generated_at ? new Date(pkg.generated_at).toLocaleDateString() : ''}`
              : pkg.status === ProjectPackageStatus.GENERATION_FAILED
                ? 'Last generation failed — try again'
                : 'Not generated',
      action: step3State !== 'done' ? 'Go to PDF Package' : undefined,
      tab: 'package',
    },
  ];

  const approvalReady = project.status === ProjectStatus.ISSUED;

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse max-w-3xl">
        <div className="h-24 bg-gray-100 rounded-2xl" />
        <div className="h-36 bg-gray-100 rounded-2xl" />
        <div className="h-36 bg-gray-100 rounded-2xl" />
        <div className="h-36 bg-gray-100 rounded-2xl" />
        <div className="h-20 bg-gray-100 rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-3xl">

      {/* ── Project identity card ─────────────────────────────────────── */}
      <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Fabrication Job</p>
            <h2 className="text-2xl font-black text-gray-900 truncate">{project.name}</h2>
            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-sm text-gray-500">
              {project.client_name && (
                <span><span className="font-semibold text-gray-700">{project.client_name}</span></span>
              )}
              {project.material && <span>{project.material}</span>}
              {project.address && <span>{project.address}</span>}
              {project.issue_date && (
                <span>Issue date: {new Date(project.issue_date).toLocaleDateString()}</span>
              )}
            </div>
          </div>
          {approvalReady && (
            <span className="shrink-0 px-3 py-1.5 bg-green-100 text-green-800 text-xs font-bold rounded-full border border-green-200">
              ✓ Issued to Client
            </span>
          )}
        </div>

        {/* Quick stats row */}
        <div className="mt-4 pt-4 border-t border-gray-100 flex items-center gap-6 text-center">
          {[
            { val: units.length,      label: 'Units'      },
            { val: unitTypes.length,  label: 'Types'      },
            { val: assemblies.length, label: 'Assemblies' },
            { val: totalParts,        label: 'Parts'      },
          ].map(({ val, label }) => (
            <div key={label}>
              <p className="text-xl font-black text-gray-900">{val}</p>
              <p className="text-xs text-gray-400 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Workflow checklist ────────────────────────────────────────── */}
      <section className="space-y-3">
        <p className="text-xs font-bold text-gray-400 uppercase tracking-widest px-1">Job Checklist</p>

        {steps.map((step) => {
          const c = stepColors[step.state];
          return (
            <div
              key={step.num}
              className={`rounded-2xl border-2 ${c.ring} ${c.bg} px-5 py-4 transition-all`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 min-w-0">
                  {/* Step number circle */}
                  <span className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center font-black text-sm ${c.num}`}>
                    {step.state === 'done' ? '✓' : step.num}
                  </span>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-bold text-gray-900 text-base leading-tight">{step.title}</h3>
                      <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${c.badge}`}>
                        {stepLabel[step.state]}
                      </span>
                    </div>
                    <p className={`text-sm mt-1 ${c.text}`}>{step.summary}</p>
                  </div>
                </div>

                {/* Action button */}
                {step.action && (
                  <button
                    onClick={() => onNavigate(step.tab)}
                    className={`shrink-0 px-4 py-2 rounded-xl text-sm font-bold transition
                      ${step.state === 'warn' || step.state === 'blocked'
                        ? 'bg-amber-500 hover:bg-amber-600 text-white'
                        : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                      }
                    `}
                  >
                    {step.action} →
                  </button>
                )}
                {!step.action && step.state === 'done' && (
                  <button
                    onClick={() => onNavigate(step.tab)}
                    className="shrink-0 px-4 py-2 rounded-xl text-sm font-medium text-gray-500 border border-gray-200 hover:bg-white transition"
                  >
                    Review
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </section>

      {/* ── Hero generate button ──────────────────────────────────────── */}
      <section>
        {allReady && pkg?.status !== ProjectPackageStatus.READY ? (
          <button
            onClick={() => onNavigate('package')}
            className="w-full py-5 bg-indigo-600 hover:bg-indigo-700 text-white font-black text-lg rounded-2xl shadow-lg transition flex items-center justify-center gap-3"
          >
            <span className="text-2xl">📄</span>
            Generate Fabrication PDF
          </button>
        ) : pkg?.status === ProjectPackageStatus.READY ? (
          <div className="rounded-2xl bg-green-50 border-2 border-green-300 px-6 py-5 flex items-center justify-between gap-4 flex-wrap">
            <div>
              <p className="font-black text-green-800 text-base">
                ✓ PDF Ready — {pkg.version}
              </p>
              <p className="text-sm text-green-600 mt-0.5">
                {pkg.page_count ?? '—'} pages
                {pkg.generated_at ? ` · Generated ${new Date(pkg.generated_at).toLocaleDateString()}` : ''}
              </p>
            </div>
            <div className="flex gap-3 flex-wrap">
              <button
                onClick={() => onNavigate('package')}
                className="px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white font-bold rounded-xl shadow transition"
              >
                Open / Download PDF
              </button>
              <button
                onClick={() => onNavigate('package')}
                className="px-5 py-2.5 border border-green-400 text-green-700 bg-white font-medium rounded-xl hover:bg-green-50 transition"
              >
                New Revision
              </button>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl bg-gray-50 border-2 border-dashed border-gray-300 px-6 py-5">
            <div className="flex items-center gap-3 opacity-60">
              <span className="text-2xl">📄</span>
              <div>
                <p className="font-bold text-gray-700">Generate Fabrication PDF</p>
                <p className="text-sm text-gray-500">
                  {steps.filter(s => s.state !== 'done').length} step{steps.filter(s => s.state !== 'done').length !== 1 ? 's' : ''} remaining before you can generate
                </p>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* ── Approval status (only shown when relevant) ────────────────── */}
      {(project.status === ProjectStatus.IN_PROGRESS || project.status === ProjectStatus.ISSUED) && (
        <section className="bg-white rounded-2xl border border-gray-200 shadow-sm px-5 py-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Approval Status</p>
              <p className="text-base font-bold text-gray-900">
                {project.status === ProjectStatus.ISSUED
                  ? 'Package issued to client'
                  : 'Fabrication in progress'}
              </p>
              {project.issue_date && (
                <p className="text-sm text-gray-500 mt-0.5">
                  Issue date: {new Date(project.issue_date).toLocaleDateString()}
                </p>
              )}
            </div>
            <button
              onClick={() => onNavigate('operations')}
              className="px-4 py-2 border border-gray-200 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 transition"
            >
              View Issues & RFIs →
            </button>
          </div>
        </section>
      )}

    </div>
  );
};
