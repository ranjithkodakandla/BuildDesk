import React from 'react';
import { TemplateDetail } from '../../types/templates';

interface Props {
  templates:  TemplateDetail[];
  loading:    boolean;
  onSelect:   (template: TemplateDetail) => void;
  recentIds?: string[];
}

// Simple geometric icons — no icon library dependency
const CATEGORY_ICON: Record<string, string> = {
  kitchen: '🍳',
  vanity:  '🪞',
  island:  '🏝️',
};

// One-line description supplement per template (sourced from production evidence — Phase 5.5)
const TEMPLATE_BLURB: Record<string, string> = {
  KITCHEN_STRAIGHT:     'Single wall run. Back splash + sink. Most common apartment kitchen.',
  KITCHEN_STRAIGHT_REF: 'Wall run with refrigerator zone at one end. Flip with Mirror.',
  KITCHEN_L:            'L-shaped two-arm kitchen. Main run + return leg. Mirror = Right Kitchen.',
  PLAIN_ISLAND:         'Freestanding island. All four edges finished. No splash or sink.',
  SINGLE_VANITY:        'Standard single sink. Back + side splashes. Default 62" — most common.',
  OFFSET_VANITY:        'Single sink shifted left or right of center.',
  DOUBLE_VANITY:        'Two evenly-spaced undermount sinks. Default 72". Master bath.',
  COMPACT_VANITY:       'Narrow vanity — 36" preset. Ideal for small baths and half-baths.',
};

const CATEGORY_ORDER = ['kitchen', 'vanity', 'island'];

function groupByCategory(templates: TemplateDetail[]): Record<string, TemplateDetail[]> {
  const groups: Record<string, TemplateDetail[]> = {};
  for (const t of templates) {
    const cat = t.definition.category;
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(t);
  }
  return groups;
}

export const TemplateGallery: React.FC<Props> = ({ templates, loading, onSelect, recentIds = [] }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-400 text-sm">
        Loading templates…
      </div>
    );
  }

  const groups = groupByCategory(templates);
  const recentTemplates = recentIds
    .map(id => templates.find(t => t.definition.id === id))
    .filter((t): t is TemplateDetail => !!t);

  return (
    <div className="space-y-8">
      <div className="text-center pb-2">
        <h2 className="text-xl font-bold text-gray-900">Choose a Template</h2>
        <p className="text-sm text-gray-500 mt-1">
          Select the countertop type to start configuring
        </p>
      </div>

      {/* ── Recently Used (Phase 6.5) ──────────────────────────────────── */}
      {recentTemplates.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-base">🕐</span>
            <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wide">Recently Used</h3>
            <div className="flex-1 h-px bg-indigo-100" />
          </div>
          <div className="flex flex-wrap gap-2">
            {recentTemplates.map(tmpl => (
              <button
                key={tmpl.definition.id}
                onClick={() => onSelect(tmpl)}
                className="
                  flex items-center gap-2 px-3 py-2 text-sm font-medium
                  bg-indigo-50 border border-indigo-200 text-indigo-700
                  rounded-xl hover:bg-indigo-100 hover:border-indigo-400
                  transition-all duration-150
                "
              >
                <span className="text-base">{CATEGORY_ICON[tmpl.definition.category] ?? '🔲'}</span>
                {tmpl.definition.display_name}
              </button>
            ))}
          </div>
        </section>
      )}

      {CATEGORY_ORDER.filter(cat => groups[cat]).map(cat => (
        <section key={cat}>
          {/* Category header */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">{CATEGORY_ICON[cat] ?? '🔲'}</span>
            <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wide">
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </h3>
            <div className="flex-1 h-px bg-gray-200" />
          </div>

          {/* Template cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {groups[cat].map(tmpl => (
              <button
                key={tmpl.definition.id}
                onClick={() => onSelect(tmpl)}
                className="
                  group text-left p-4 rounded-xl border-2 border-gray-200
                  bg-white hover:border-indigo-400 hover:shadow-md
                  transition-all duration-150 focus:outline-none
                  focus:ring-2 focus:ring-indigo-400 focus:ring-offset-2
                "
              >
                {/* Mini illustration */}
                <div className="mb-3 flex items-center justify-center h-14 rounded-lg bg-gray-50 group-hover:bg-indigo-50 transition-colors">
                  <TemplateIllustration templateId={tmpl.definition.id} category={cat} />
                </div>

                {/* Name */}
                <p className="font-semibold text-gray-900 text-sm leading-tight">
                  {tmpl.definition.display_name}
                </p>

                {/* Short description */}
                <p className="text-xs text-gray-500 mt-1 leading-snug">
                  {TEMPLATE_BLURB[tmpl.definition.id] ?? tmpl.definition.description}
                </p>

                {/* Feature pills */}
                <div className="mt-2 flex flex-wrap gap-1">
                  {tmpl.definition.supported_features.slice(0, 3).map(f => (
                    <span
                      key={f}
                      className="px-1.5 py-0.5 text-xs rounded-full bg-gray-100 text-gray-500"
                    >
                      {f.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>

                <div className="mt-3 text-xs font-semibold text-indigo-600 group-hover:text-indigo-700">
                  Select →
                </div>
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
};

// ─── Inline SVG illustrations ────────────────────────────────────────────────

function TemplateIllustration({
  templateId,
  category,
}: {
  templateId: string;
  category: string;
}) {
  const cls = 'fill-none stroke-current';
  const w = 80;
  const h = 44;

  if (category === 'island') {
    // Freestanding rectangle (all edges thick)
    return (
      <svg width={w} height={h} viewBox="0 0 80 44" className="text-indigo-400">
        <rect x="10" y="8" width="60" height="28" rx="2" strokeWidth="2.5" className={cls} />
      </svg>
    );
  }

  if (templateId === 'DOUBLE_VANITY') {
    // Wide rectangle with two sink ovals
    return (
      <svg width={w} height={h} viewBox="0 0 80 44" className="text-indigo-400">
        <rect x="4" y="8" width="72" height="28" rx="2" strokeWidth="2" className={cls} />
        <ellipse cx="24" cy="22" rx="8" ry="6" strokeWidth="1.5" strokeDasharray="3,2" className={cls} />
        <ellipse cx="56" cy="22" rx="8" ry="6" strokeWidth="1.5" strokeDasharray="3,2" className={cls} />
      </svg>
    );
  }

  if (templateId === 'KITCHEN_STRAIGHT_REF') {
    // Counter with REF zone marker
    return (
      <svg width={w} height={h} viewBox="0 0 80 44" className="text-indigo-400">
        <rect x="4" y="10" width="52" height="24" rx="2" strokeWidth="2" className={cls} />
        <rect x="56" y="10" width="20" height="24" rx="2" strokeWidth="1.5" strokeDasharray="3,2" className={cls} />
        <text x="65" y="25" fontSize="6" textAnchor="middle" fill="currentColor" stroke="none" className="font-bold">REF</text>
      </svg>
    );
  }

  if (templateId === 'KITCHEN_L') {
    // L-shaped: main horizontal run + perpendicular return at left end
    return (
      <svg width={w} height={h} viewBox="0 0 80 44" className="text-indigo-400">
        {/* Main run */}
        <rect x="4" y="18" width="56" height="20" rx="2" strokeWidth="2" className={cls} />
        {/* Return leg going up from left */}
        <rect x="4" y="6" width="20" height="14" rx="2" strokeWidth="2" className={cls} />
        {/* Sink in main run */}
        <rect x="20" y="22" width="14" height="10" rx="1.5" strokeWidth="1.5" strokeDasharray="3,2" className={cls} />
      </svg>
    );
  }

  if (category === 'kitchen') {
    // Long rectangle (kitchen straight)
    return (
      <svg width={w} height={h} viewBox="0 0 80 44" className="text-indigo-400">
        <rect x="4" y="10" width="72" height="24" rx="2" strokeWidth="2" className={cls} />
        <rect x="26" y="14" width="16" height="12" rx="2" strokeWidth="1.5" strokeDasharray="3,2" className={cls} />
      </svg>
    );
  }

  // Vanity (with optional splash indicator at back)
  return (
    <svg width={w} height={h} viewBox="0 0 80 44" className="text-indigo-400">
      {/* Main top */}
      <rect x="10" y="12" width="60" height="24" rx="2" strokeWidth="2" className={cls} />
      {/* Back splash hint */}
      <rect x="10" y="8" width="60" height="4" rx="1" strokeWidth="1" className={cls} />
      {/* Sink oval */}
      <ellipse cx="40" cy="24" rx="10" ry="7" strokeWidth="1.5" strokeDasharray="3,2" className={cls} />
    </svg>
  );
}
