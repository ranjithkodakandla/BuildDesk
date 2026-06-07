import React from 'react';

interface Props {
  svg:              string | null;
  loading:          boolean;
  error:            string | null;
  templateName?:    string;
  readinessLabel?:  string;
  readinessOk?:     boolean;
}

export const TemplatePreview: React.FC<Props> = ({
  svg, loading, error, templateName, readinessLabel, readinessOk,
}) => {
  return (
    <div className="flex flex-col h-full min-h-64">
      {/* Header */}
      <div className="flex items-center justify-between mb-2 px-1">
        <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">
          Live Preview
        </p>
        {loading && (
          <span className="text-xs text-indigo-500 flex items-center gap-1">
            <span className="w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin inline-block" />
            Rendering…
          </span>
        )}
        {!loading && readinessLabel && (
          <span className={`text-xs font-medium flex items-center gap-1 ${readinessOk ? 'text-green-600' : 'text-amber-600'}`}>
            <span className={`w-1.5 h-1.5 rounded-full inline-block ${readinessOk ? 'bg-green-500' : 'bg-amber-400'}`} />
            {readinessLabel}
          </span>
        )}
        {!loading && !readinessLabel && svg && (
          <span className="text-xs text-green-600 font-medium flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
            PDF Ready
          </span>
        )}
      </div>

      {/* Preview area */}
      <div className={`
        flex-1 rounded-xl border-2 overflow-hidden bg-white relative
        ${loading ? 'border-indigo-200' : error ? 'border-red-200' : 'border-gray-200'}
      `}>

        {/* SVG rendered inline */}
        {svg && !loading && (
          <div
            className="w-full h-full"
            dangerouslySetInnerHTML={{ __html: svg }}
            style={{ lineHeight: 0 }}
          />
        )}

        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 bg-white/80 flex items-center justify-center" aria-live="polite">
            <div className="text-center">
              <div
                className="w-8 h-8 border-[3px] border-indigo-400 border-t-transparent rounded-full animate-spin mx-auto mb-2"
                aria-label="Loading preview"
                role="status"
              />
              <p className="text-xs text-gray-500">Generating preview…</p>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!svg && !loading && !error && (
          <div className="absolute inset-0 flex items-center justify-center text-center px-4">
            <div>
              <div className="text-5xl mb-3 opacity-20">📐</div>
              <p className="text-sm text-gray-500 font-medium">
                {templateName ? `Configure ${templateName}` : 'Configure your template'}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Preview updates automatically as you change settings
              </p>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div className="absolute inset-0 flex items-center justify-center text-center px-6" role="alert">
            <div>
              <div className="text-3xl mb-2">⚠️</div>
              <p className="text-sm text-red-600 font-semibold mb-1">Preview unavailable</p>
              <p className="text-xs text-gray-500 leading-relaxed">{error}</p>
            </div>
          </div>
        )}
      </div>

      {/* Scale note */}
      {svg && !loading && (
        <p className="text-xs text-gray-400 mt-1.5 px-1 text-center">
          Scale: NTS — for fabrication reference only
        </p>
      )}
    </div>
  );
};
