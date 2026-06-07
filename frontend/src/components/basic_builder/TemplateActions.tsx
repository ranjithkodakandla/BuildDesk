import React, { useState } from 'react';
import { templatesApi } from '../../api/templates';
import { TemplateGenerateRequest } from '../../types/templates';

interface Props {
  requestBody:      TemplateGenerateRequest | null;
  templateName:     string;
  projectName?:     string;
  warnings:         string[];
  onPreviewRequest: () => void;
  previewLoading:   boolean;
  readinessLabel?:  string;
  readinessOk?:     boolean;
  onExportJson?:    () => void;
  onSaveToProject?: () => Promise<void>;
  saveStatus?:      'idle' | 'saving' | 'saved' | 'error';
  savedAssemblyId?: string | null;
  onViewDrawings?:  () => void;
}

export const TemplateActions: React.FC<Props> = ({
  requestBody,
  templateName,
  projectName,
  warnings,
  onPreviewRequest,
  previewLoading,
  readinessLabel,
  readinessOk,
  onExportJson,
  onSaveToProject,
  saveStatus = 'idle',
  onViewDrawings,
}) => {
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  async function handleDownloadPdf() {
    if (!requestBody) return;
    setPdfLoading(true);
    setPdfError(null);
    try {
      const blob = await templatesApi.pdf(requestBody);
      const w        = requestBody.width  ? `${requestBody.width}` : '';
      const d        = requestBody.depth  ? `x${requestBody.depth}` : '';
      const tmplSlug = templateName.replace(/\s+/g, '-').toLowerCase();
      const projSlug = projectName
        ? projectName.replace(/[^a-zA-Z0-9]+/g, '-').toLowerCase().slice(0, 24)
        : '';
      const dims     = w ? `_${w}${d}` : '';
      const filename = projSlug
        ? `${projSlug}_${tmplSlug}${dims}.pdf`
        : `${tmplSlug}${dims}.pdf`;
      const url  = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href     = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch {
      setPdfError('PDF generation failed. Please try again.');
    } finally {
      setPdfLoading(false);
    }
  }

  const disabled = !requestBody || previewLoading;

  return (
    <div className="space-y-2">
      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="rounded bg-amber-50 border border-amber-200 px-3 py-2">
          {warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-700">⚠ {w}</p>
          ))}
        </div>
      )}

      {/* Readiness status */}
      {readinessLabel && (
        <div className={`flex items-center gap-1.5 py-1.5 px-3 rounded text-[10px] font-medium ${
          readinessOk
            ? 'bg-green-50 border border-green-200 text-green-700'
            : 'bg-amber-50 border border-amber-200 text-amber-700'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
            readinessOk ? 'bg-green-500' : 'bg-amber-400'
          }`} />
          {readinessLabel}
        </div>
      )}

      {/* PRIMARY: Save Drawing to Project */}
      {onSaveToProject && (
        <div className="space-y-1">
          <button
            onClick={onSaveToProject}
            disabled={!requestBody || saveStatus === 'saving' || saveStatus === 'saved'}
            className={`w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition ${
              saveStatus === 'saved'
                ? 'bg-[#047857] text-white cursor-default'
                : !requestBody || saveStatus === 'saving'
                  ? 'bg-[#f1f5f9] text-[#94a3b8] cursor-not-allowed'
                  : 'btn-primary'
            }`}
          >
            {saveStatus === 'saving' ? (
              <>
                <span className="w-3 h-3 border-2 border-[#334155] border-t-transparent rounded-full animate-spin" />
                Saving…
              </>
            ) : saveStatus === 'saved' ? (
              <>✓ Saved to Shop Drawings</>
            ) : (
              <>⬆ Save Drawing to Project</>
            )}
          </button>
          {saveStatus === 'saved' && onViewDrawings && (
            <button
              onClick={onViewDrawings}
              className="w-full text-[10px] py-1 rounded border border-green-300 text-green-700 hover:bg-green-50 transition"
            >
              View in Shop Drawings →
            </button>
          )}
          {saveStatus === 'error' && (
            <p className="text-xs text-red-500 text-center">Save failed. Please try again.</p>
          )}
        </div>
      )}

      {/* SECONDARY: Download PDF */}
      <button
        onClick={handleDownloadPdf}
        disabled={disabled || pdfLoading}
        className={`w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium border transition ${
          disabled || pdfLoading
            ? 'border-[#e2e8f0] text-[#cbd5e1] cursor-not-allowed'
            : 'border-[#e2e8f0] text-[#475569] hover:bg-[#f8fafc]'
        }`}
      >
        {pdfLoading ? (
          <>
            <span className="w-3 h-3 border-2 border-[#334155] border-t-transparent rounded-full animate-spin" />
            Generating…
          </>
        ) : (
          <>↓ Download PDF</>
        )}
      </button>

      {pdfError && (
        <p className="text-xs text-red-500 text-center">{pdfError}</p>
      )}

      {/* TERTIARY: Advanced options (collapsed by default) */}
      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced(v => !v)}
          className="text-[10px] text-[#94a3b8] hover:text-[#475569] transition flex items-center gap-1"
        >
          {showAdvanced ? '▲' : '▼'} More options
        </button>
        {showAdvanced && (
          <div className="mt-1.5 space-y-1.5">
            <button
              onClick={onPreviewRequest}
              disabled={disabled}
              className={`w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded border text-xs font-medium transition ${
                disabled
                  ? 'border-[#e2e8f0] text-[#cbd5e1] cursor-not-allowed'
                  : 'border-[#e2e8f0] text-[#475569] hover:bg-[#f8fafc]'
              }`}
            >
              {previewLoading ? (
                <span className="w-3 h-3 border-2 border-[#334155] border-t-transparent rounded-full animate-spin" />
              ) : (
                <span>↻</span>
              )}
              Refresh Preview
            </button>
            {onExportJson && (
              <button
                type="button"
                onClick={onExportJson}
                disabled={!requestBody}
                className="w-full text-[10px] py-1.5 rounded border border-[#e2e8f0] text-[#94a3b8] hover:text-[#475569] hover:border-[#cbd5e1] transition disabled:opacity-40"
                title="Export the current configuration as a JSON file"
              >
                ↓ Export config (JSON)
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
