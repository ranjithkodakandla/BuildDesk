import React, { useState } from 'react';
import { BuilderConfig, TemplateDetail, UIFieldSpec } from '../../types/templates';
import { getNestedValue, setNestedValue } from './configUtils';

// ── Quick preset definitions (from production evidence — Phase 5.5) ──────────
const WIDTH_PRESETS: Record<string, number[]> = {
  SINGLE_VANITY:        [36, 48, 60, 62],
  OFFSET_VANITY:        [48, 55, 60, 62],
  DOUBLE_VANITY:        [60, 72, 84, 96],
  COMPACT_VANITY:       [22, 28, 36],
  KITCHEN_STRAIGHT:     [60, 72, 84, 96, 120],
  KITCHEN_STRAIGHT_REF: [84, 96, 108, 120],
  KITCHEN_L:            [72, 84, 96],
  PLAIN_ISLAND:         [36, 44, 60, 72],
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyConfig = Record<string, any>;

interface Props {
  template: TemplateDetail;
  config: BuilderConfig;
  onChange: (config: BuilderConfig) => void;
}

const SELECT_LABELS: Record<string, Record<string, string>> = {
  'edge_finish': {
    polished: 'Polished',
    eased:    'Eased',
    miter:    'Miter (Waterfall)',
    flat:     'Flat Polish',
  },
  'sink.type': {
    none:      'No Sink',
    oval:      'Undermount Oval',
    rectangle: 'Undermount Rectangle',
  },
  'sink.position': {
    center: 'Center',
    left:   'Left Side',
    right:  'Right Side',
  },
  'sink.size': {
    small:    'Small',
    standard: 'Standard',
    large:    'Large',
  },
};

function optionLabel(fieldKey: string, value: string): string {
  return SELECT_LABELS[fieldKey]?.[value] ?? value.charAt(0).toUpperCase() + value.slice(1);
}

export const TemplateConfigurator: React.FC<Props> = ({ template, config, onChange }) => {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const { ui_contract } = template;
  const visibleFields = ui_contract.fields.filter((f: UIFieldSpec) => f.visible);

  const dimensionKeys  = new Set(['width', 'depth', 'thickness']);
  const splashKeys     = new Set(['splash.back', 'splash.left', 'splash.right', 'splash.height']);
  const sinkKeys       = new Set(['sink.type', 'sink.position', 'sink.size']);
  const styleKeys      = new Set(['edge_finish', 'mirror']);

  const dimensions = visibleFields.filter(f => dimensionKeys.has(f.key));
  const splashes   = visibleFields.filter(f => splashKeys.has(f.key));
  const sinks      = visibleFields.filter(f => sinkKeys.has(f.key));
  const style      = visibleFields.filter(f => styleKeys.has(f.key));

  const anySplashOn = config.splash.back || config.splash.left || config.splash.right;

  function handleChange(key: string, value: unknown) {
    onChange(setNestedValue(config as AnyConfig, key, value) as BuilderConfig);
  }

  const sinkType = config.sink.type;

  return (
    <div className="space-y-4">
      {/* ── Dimensions ─────────────────────────────────────────────────── */}
      {dimensions.length > 0 && (
        <Section title="Dimensions">
          <div className="grid grid-cols-2 gap-2">
            {dimensions.map(f => (
              <NumberField
                key={f.key}
                field={f}
                value={getNestedValue(config as AnyConfig, f.key) as number}
                onChange={v => handleChange(f.key, v)}
                label={f.key === 'width' ? ui_contract.dimension_term : f.label}
              />
            ))}
          </div>
          {WIDTH_PRESETS[ui_contract.template_id] && (
            <div className="mt-2">
              <p className="text-[10px] text-[#94a3b8] mb-1">
                Quick presets ({ui_contract.dimension_term.toLowerCase()}):
              </p>
              <div className="flex flex-wrap gap-1">
                {WIDTH_PRESETS[ui_contract.template_id].map(preset => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => handleChange('width', preset)}
                    className={`px-2 py-0.5 text-[10px] rounded border transition-colors ${
                      (getNestedValue(config as AnyConfig, 'width') as number) === preset
                        ? 'border-[#1e293b] bg-[#f1f5f9] text-[#1e293b] font-semibold'
                        : 'border-[#e2e8f0] bg-white text-[#64748b] hover:border-[#94a3b8]'
                    }`}
                  >
                    {preset}"
                  </button>
                ))}
              </div>
            </div>
          )}
        </Section>
      )}

      {/* ── Sink ───────────────────────────────────────────────────────── */}
      {sinks.length > 0 && (
        <Section title="Sink">
          <div className="space-y-2">
            {sinks
              .filter(f => f.key === 'sink.type')
              .map(f => (
                <SelectField
                  key={f.key}
                  field={f}
                  value={getNestedValue(config as AnyConfig, f.key) as string}
                  onChange={v => handleChange(f.key, v)}
                />
              ))}
            {sinkType !== 'none' && (
              <>
                {sinks
                  .filter(f => f.key !== 'sink.type')
                  .map(f => (
                    <SelectField
                      key={f.key}
                      field={f}
                      value={getNestedValue(config as AnyConfig, f.key) as string}
                      onChange={v => handleChange(f.key, v)}
                    />
                  ))}
                {/* Sink model number — prints on PDF Sink Info section */}
                <label className="block">
                  <span className="label-text">
                    Sink Model #
                    <span className="text-[#94a3b8] font-normal ml-1">(prints on PDF)</span>
                  </span>
                  <input
                    type="text"
                    value={(getNestedValue(config as AnyConfig, 'sink.model') as string) ?? ''}
                    onChange={e => handleChange('sink.model', e.target.value)}
                    placeholder="e.g. CS-1417"
                    className="input-field"
                  />
                </label>
              </>
            )}
          </div>
        </Section>
      )}

      {/* ── Work Ticket # ──────────────────────────────────────────────── */}
      <Section title="Drawing Info">
        <label className="block">
          <span className="label-text">
            Work Ticket Number
            <span className="text-[#94a3b8] font-normal ml-1">(e.g. 1041-01)</span>
          </span>
          <input
            type="text"
            value={(getNestedValue(config as AnyConfig, 'ticket_number') as string) ?? ''}
            onChange={e => handleChange('ticket_number', e.target.value)}
            placeholder="1041-01"
            className="input-field"
          />
        </label>
      </Section>

      {/* ── Backsplash — always visible (on nearly every drawing) ──────── */}
      {splashes.length > 0 && (
        <Section title="Backsplash / Side Splash">
          <div className="space-y-2">
            {splashes
              .filter(f => f.key !== 'splash.height')
              .map(f => (
                <BoolField
                  key={f.key}
                  field={f}
                  value={getNestedValue(config as AnyConfig, f.key) as boolean}
                  onChange={v => handleChange(f.key, v)}
                />
              ))}
            {anySplashOn &&
              splashes
                .filter(f => f.key === 'splash.height')
                .map(f => (
                  <div key={f.key} className="pt-1">
                    <NumberField
                      field={f}
                      value={getNestedValue(config as AnyConfig, f.key) as number}
                      onChange={v => handleChange(f.key, v)}
                      label="Splash Height (inches)"
                      min={1}
                      max={12}
                      step={0.5}
                    />
                  </div>
                ))}
          </div>
        </Section>
      )}

      {/* ── Finish & Layout (edge, mirror) — collapsed ───────────────── */}
      {style.length > 0 && (
        <>
          <button
            type="button"
            onClick={() => setAdvancedOpen(v => !v)}
            className="flex items-center gap-1.5 text-[11px] text-[#94a3b8] hover:text-[#475569] transition w-full text-left"
          >
            <span className="text-[9px]">{advancedOpen ? '▲' : '▼'}</span>
            {advancedOpen ? 'Hide' : 'Finish & Layout'} — Edge style, Mirror
          </button>
          {advancedOpen && (
            <Section title="Finish & Layout">
              <div className="space-y-2">
                {style.map(f =>
                  f.field_type === 'select' ? (
                    <SelectField
                      key={f.key}
                      field={f}
                      value={getNestedValue(config as AnyConfig, f.key) as string}
                      onChange={v => handleChange(f.key, v)}
                    />
                  ) : (
                    <BoolField
                      key={f.key}
                      field={f}
                      value={getNestedValue(config as AnyConfig, f.key) as boolean}
                      onChange={v => handleChange(f.key, v)}
                    />
                  )
                )}
              </div>
            </Section>
          )}
        </>
      )}
    </div>
  );
};

// ─── Section wrapper ──────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10px] font-bold text-[#94a3b8] uppercase tracking-wider mb-2">
        {title}
      </p>
      {children}
    </div>
  );
}

// ─── Field atoms ──────────────────────────────────────────────────────────────

interface NumberFieldProps {
  field: UIFieldSpec;
  value: number;
  onChange: (v: number) => void;
  label?: string;
  min?: number;
  max?: number;
  step?: number;
}

function NumberField({ field, value, onChange, label, min, max, step }: NumberFieldProps) {
  return (
    <label className="block">
      <span className="label-text">
        {label ?? field.label}
        {field.unit && <span className="text-[#94a3b8] font-normal ml-1">({field.unit})</span>}
      </span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step ?? 0.5}
        onChange={e => onChange(parseFloat(e.target.value) || 0)}
        className="input-field tabular-nums"
        title={field.hint ?? undefined}
      />
    </label>
  );
}

interface BoolFieldProps {
  field: UIFieldSpec;
  value: boolean;
  onChange: (v: boolean) => void;
}

function BoolField({ field, value, onChange }: BoolFieldProps) {
  const id = `field-${field.key.replace('.', '-')}`;
  return (
    <label
      htmlFor={id}
      className="flex items-center gap-2.5 cursor-pointer group select-none"
      title={field.hint ?? undefined}
    >
      <div className={`relative w-8 h-5 rounded-full transition-colors duration-200 ${
        value ? 'bg-[#1e293b]' : 'bg-[#cbd5e1]'
      }`}>
        <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${
          value ? 'translate-x-3' : 'translate-x-0.5'
        }`} />
        <input
          type="checkbox"
          id={id}
          checked={value}
          onChange={e => onChange(e.target.checked)}
          className="sr-only"
        />
      </div>
      <span className="text-xs text-[#334155] group-hover:text-[#1e293b]">
        {field.label}
      </span>
    </label>
  );
}

interface SelectFieldProps {
  field: UIFieldSpec;
  value: string;
  onChange: (v: string) => void;
}

function SelectField({ field, value, onChange }: SelectFieldProps) {
  return (
    <label className="block">
      <span className="label-text">{field.label}</span>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="input-field"
        title={field.hint ?? undefined}
      >
        {(field.options ?? []).map(opt => (
          <option key={opt} value={opt}>
            {optionLabel(field.key, opt)}
          </option>
        ))}
      </select>
    </label>
  );
}
