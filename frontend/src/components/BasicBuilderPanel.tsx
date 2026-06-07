import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Project } from '../types/hierarchy';
import { BuilderConfig, TemplateDetail, TemplateGenerateRequest } from '../types/templates';
import { templatesApi } from '../api/templates';
import { TemplateGallery } from './basic_builder/TemplateGallery';
import { TemplateConfigurator } from './basic_builder/TemplateConfigurator';
import { TemplatePreview } from './basic_builder/TemplatePreview';
import { TemplateActions } from './basic_builder/TemplateActions';
import { buildRequestBody, defaultConfigFromTemplate } from './basic_builder/configUtils';

// ---------------------------------------------------------------------------
// localStorage helpers — recent templates + saved config per template
// ---------------------------------------------------------------------------

const _LS_RECENT = 'bd_recent_templates_v1';
const _LS_CFG    = (id: string) => `bd_cfg_v1_${id}`;
const MAX_RECENT = 4;

function getRecentTemplateIds(): string[] {
  try { return JSON.parse(localStorage.getItem(_LS_RECENT) ?? '[]'); }
  catch { return []; }
}

function pushRecentTemplate(id: string): void {
  const prev = getRecentTemplateIds().filter(x => x !== id);
  try { localStorage.setItem(_LS_RECENT, JSON.stringify([id, ...prev].slice(0, MAX_RECENT))); }
  catch { /* storage full — ignore */ }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function getSavedConfig(id: string): Record<string, any> | null {
  try { const v = localStorage.getItem(_LS_CFG(id)); return v ? JSON.parse(v) : null; }
  catch { return null; }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function saveConfig(id: string, cfg: Record<string, any>): void {
  try { localStorage.setItem(_LS_CFG(id), JSON.stringify(cfg)); }
  catch { /* storage full — ignore */ }
}

// ---------------------------------------------------------------------------
// Preview readiness helpers
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function getReadinessLabel(config: Record<string, any> | null, svg: string | null): { label: string; ok: boolean } {
  if (!config) return { label: 'Select a template', ok: false };
  if (!config.width || Number(config.width) <= 0) return { label: 'Set a width', ok: false };
  const sinkType = config?.sink?.type ?? config?.sink_type;
  if (sinkType === undefined || sinkType === null) return { label: 'Select sink type', ok: false };
  if (!svg) return { label: 'Generating preview…', ok: false };
  return { label: 'Ready To Generate ✓', ok: true };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyObj = Record<string, any>;

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface Props {
  project:            Project;
  initialTemplateId?: string;
  onAssemblySaved?:   () => void;
  onViewDrawings?:    () => void;
}

export const BasicBuilderPanel: React.FC<Props> = ({
  project,
  initialTemplateId,
  onAssemblySaved,
  onViewDrawings,
}) => {
  // ── Template list ────────────────────────────────────────────────────────
  const [templates, setTemplates]         = useState<TemplateDetail[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(true);

  // ── Selected template + config ──────────────────────────────────────────
  const [selected, setSelected]     = useState<TemplateDetail | null>(null);
  const [config, setConfig]         = useState<BuilderConfig | null>(null);
  const [recentIds, setRecentIds]   = useState<string[]>(() => getRecentTemplateIds());

  // ── Preview state ────────────────────────────────────────────────────────
  const [previewSvg, setPreviewSvg]       = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError]   = useState<string | null>(null);
  const [warnings, setWarnings]           = useState<string[]>([]);

  // ── Save-to-project state (Phase 8) ──────────────────────────────────────
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Load template list on mount ──────────────────────────────────────────
  useEffect(() => {
    setTemplatesLoading(true);
    templatesApi
      .listTemplates()
      .then(setTemplates)
      .catch(console.error)
      .finally(() => setTemplatesLoading(false));
  }, []);

  // ── Auto-refresh preview when config changes (debounced 600 ms) ──────────
  useEffect(() => {
    if (!config) return;
    // Persist config for recall on next visit
    if (selected) saveConfig(selected.definition.id, config as unknown as AnyObj);
    // Reset save status when config changes — user modified something
    setSaveStatus('idle');
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      triggerPreview(config, false);
    }, 600);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config]);

  // ── Auto-select initialTemplateId when templates load (Phase 8) ─────────
  useEffect(() => {
    if (!initialTemplateId || !templates.length || selected) return;
    const match = templates.find(t => t.definition.id === initialTemplateId);
    if (match) selectTemplate(match);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialTemplateId, templates]);

  // ── Select template (with recent list + config recall) ───────────────────
  function selectTemplate(tmpl: TemplateDetail) {
    const id = tmpl.definition.id;
    // Try to restore last-used config for this template
    const saved = getSavedConfig(id);
    const initial = saved
      ? (saved as unknown as BuilderConfig)
      : (defaultConfigFromTemplate(id, tmpl.definition.defaults as AnyObj) as unknown as BuilderConfig);
    setSelected(tmpl);
    setConfig(initial);
    setPreviewSvg(null);
    setPreviewError(null);
    setWarnings([]);
    pushRecentTemplate(id);
    setRecentIds(getRecentTemplateIds());
  }

  // ── Request preview from API (Phase 7: only SVG, no double-call) ────────
  const triggerPreview = useCallback(async (cfg: BuilderConfig, withWarnings = false) => {
    if (!cfg) return;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const body = buildRequestBody(
        cfg as unknown as AnyObj,
        project.project_id,
      ) as unknown as TemplateGenerateRequest;

      const svg = await templatesApi.preview(body);
      setPreviewSvg(svg);

      // Fetch warnings only when explicitly requested (PDF download or manual refresh)
      if (withWarnings) {
        const generated = await templatesApi.generate(body);
        setWarnings(generated.warnings ?? []);
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'Unknown error';
      setPreviewError(`Preview failed — ${errMsg}. Check your configuration and try again.`);
    } finally {
      setPreviewLoading(false);
    }
  }, [project.project_id]);

  // ── Reset template to defaults ────────────────────────────────────────────
  function resetToDefaults() {
    if (!selected) return;
    const fresh = defaultConfigFromTemplate(
      selected.definition.id,
      selected.definition.defaults as AnyObj,
    ) as unknown as BuilderConfig;
    setConfig(fresh);
    setPreviewSvg(null);
    setWarnings([]);
  }

  // ── Save drawing to project (Phase 8) ────────────────────────────────────
  async function saveToProject() {
    if (!requestBody) return;
    setSaveStatus('saving');
    try {
      await templatesApi.saveToProject(requestBody);
      setSaveStatus('saved');
      onAssemblySaved?.();
    } catch {
      setSaveStatus('error');
    }
  }

  // ── Derived request body for actions ────────────────────────────────────
  const requestBody = config
    ? (buildRequestBody(
        config as unknown as AnyObj,
        project.project_id,
      ) as unknown as TemplateGenerateRequest)
    : null;

  // ── Preview readiness label ───────────────────────────────────────────────
  const readiness = getReadinessLabel(config as unknown as AnyObj | null, previewSvg);

  // ── JSON config export ────────────────────────────────────────────────────
  function exportConfigJson() {
    if (!requestBody || !selected) return;
    const payload = {
      exported_at:   new Date().toISOString(),
      template:      selected.definition.id,
      template_name: selected.definition.display_name,
      config:        requestBody,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const base = selected.definition.display_name.replace(/\s+/g, '-').toLowerCase();
    link.href     = url;
    link.download = `${base}-config.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* ── Breadcrumb when template is selected ────────────────────────── */}
      {selected && (
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setSelected(null); setConfig(null); setPreviewSvg(null); }}
            className="text-xs text-[#94a3b8] hover:text-[#3b82f6] transition"
          >
            ← Templates
          </button>
          <span className="text-[#e2e8f0]">|</span>
          <span className="text-xs font-semibold text-[#334155]">
            {selected.definition.display_name}
          </span>
          <span className={`
            text-[10px] px-1.5 py-0.5 rounded font-medium
            ${selected.definition.category === 'kitchen'
              ? 'bg-orange-100 text-orange-700'
              : selected.definition.category === 'island'
              ? 'bg-blue-100 text-blue-700'
              : 'bg-purple-100 text-purple-700'
            }
          `}>
            {selected.definition.category}
          </span>
        </div>
      )}

      {/* ── Gallery: no template selected ──────────────────────────────── */}
      {!selected && (
        <TemplateGallery
          templates={templates}
          loading={templatesLoading}
          onSelect={selectTemplate}
          recentIds={recentIds}
        />
      )}

      {/* ── Configurator + Preview: template selected ───────────────────── */}
      {selected && config && (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">

          {/* Left: form (2 of 5 columns) */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded border border-[#e2e8f0] p-4 space-y-1">
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-bold text-[#94a3b8] uppercase tracking-wider">
                  Configuration
                </p>
                <button
                  onClick={resetToDefaults}
                  className="text-xs text-[#94a3b8] hover:text-[#3b82f6] transition underline"
                  title="Reset all fields to template defaults"
                  aria-label="Reset to defaults"
                >
                  Reset
                </button>
              </div>
              <TemplateConfigurator
                template={selected}
                config={config}
                onChange={setConfig}
              />
            </div>
          </div>

          {/* Right: preview + actions (3 of 5 columns) */}
          <div className="lg:col-span-3 flex flex-col gap-3">

            {/* SVG preview */}
            <div className="bg-white rounded border border-[#e2e8f0] p-3 flex-1">
              <TemplatePreview
                svg={previewSvg}
                loading={previewLoading}
                error={previewError}
                templateName={selected.definition.display_name}
                readinessLabel={readiness.label}
                readinessOk={readiness.ok}
              />
            </div>

            {/* Action buttons */}
            <div className="bg-white rounded border border-[#e2e8f0] p-3">
              <TemplateActions
                requestBody={requestBody}
                templateName={selected.definition.display_name}
                projectName={project.name}
                warnings={warnings}
                onPreviewRequest={() => config && triggerPreview(config, true)}
                previewLoading={previewLoading}
                readinessLabel={readiness.label}
                readinessOk={readiness.ok}
                onExportJson={exportConfigJson}
                onSaveToProject={saveToProject}
                saveStatus={saveStatus}
                onViewDrawings={onViewDrawings}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
