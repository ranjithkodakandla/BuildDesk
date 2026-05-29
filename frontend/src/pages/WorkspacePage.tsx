import React, { useState, useCallback } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import {
  geometryApi,
  exportApi,
  type GeometryResponse,
  type ShapeType,
  SHAPE_DIMENSIONS,
} from '../api/geometry';

const SHAPES: ShapeType[] = ['rectangle', 'island', 'vanity', 'straight_kitchen', 'l_kitchen'];
const PROJECT_ID = '22222222-2222-2222-2222-222222222222'; // demo project

export const WorkspacePage: React.FC = () => {
  const { user, tenantId, logout } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const initialShape = (searchParams.get('shape') as ShapeType) || 'rectangle';

  const [selectedShape, setSelectedShape] = useState<ShapeType>(initialShape);
  const [dimensions, setDimensions] = useState<Record<string, number>>(() => {
    const fields = SHAPE_DIMENSIONS[initialShape];
    return Object.fromEntries(fields.map((f) => [f.key, f.defaultValue]));
  });
  const [result, setResult] = useState<GeometryResponse | null>(null);
  const [svgContent, setSvgContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState<'svg' | 'pdf' | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleShapeChange = (shape: ShapeType) => {
    setSelectedShape(shape);
    const fields = SHAPE_DIMENSIONS[shape];
    setDimensions(Object.fromEntries(fields.map((f) => [f.key, f.defaultValue])));
    setResult(null);
    setSvgContent(null);
    setError(null);
  };

  const buildRequest = useCallback(
    () => ({
      shape_type: selectedShape,
      project_id: PROJECT_ID,
      tenant_id: tenantId!,
      dimensions,
    }),
    [selectedShape, tenantId, dimensions]
  );

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setSvgContent(null);
    try {
      const { data } = await geometryApi.create(buildRequest());
      setResult(data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to generate geometry.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleSvgExport = async () => {
    setExportLoading('svg');
    setError(null);
    try {
      const { data } = await exportApi.svg(buildRequest());
      setSvgContent(data as string);
    } catch {
      setError('SVG export failed.');
    } finally {
      setExportLoading(null);
    }
  };

  const handlePdfExport = async () => {
    setExportLoading('pdf');
    setError(null);
    try {
      const { data } = await exportApi.pdf(buildRequest());
      const url = URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `buildesk-${selectedShape}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('PDF export failed.');
    } finally {
      setExportLoading(null);
    }
  };

  const shapeLabel = (s: ShapeType) =>
    s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Nav */}
      <nav className="border-b border-slate-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
                <span className="text-white font-bold text-sm">B</span>
              </div>
              <span className="text-white font-semibold">BuildDesk</span>
            </Link>
            <span className="text-slate-700">/</span>
            <span className="text-slate-400 text-sm">Workspace</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-slate-500 text-sm">{user?.email}</span>
            <button
              onClick={() => { logout(); navigate('/login'); }}
              className="text-sm text-slate-400 hover:text-white transition-colors px-3 py-1.5 border border-slate-700 rounded-lg hover:border-slate-600"
            >
              Sign out
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-6 py-8 flex gap-6">
        {/* Left: Controls */}
        <div className="w-80 flex-shrink-0 space-y-5">
          {/* Shape selector */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Surface Type
            </h3>
            <div className="space-y-1.5">
              {SHAPES.map((s) => (
                <button
                  key={s}
                  onClick={() => handleShapeChange(s)}
                  className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm transition-all ${
                    selectedShape === s
                      ? 'bg-violet-600 text-white font-medium'
                      : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  {shapeLabel(s)}
                </button>
              ))}
            </div>
          </div>

          {/* Dimensions */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Dimensions
            </h3>
            <div className="space-y-4">
              {SHAPE_DIMENSIONS[selectedShape].map((field) => (
                <div key={field.key}>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    {field.label}
                    {field.unit && (
                      <span className="ml-1 text-slate-500 font-normal">({field.unit})</span>
                    )}
                  </label>
                  <input
                    type="number"
                    value={dimensions[field.key] ?? field.defaultValue}
                    min={field.min}
                    max={field.max}
                    onChange={(e) =>
                      setDimensions((prev) => ({
                        ...prev,
                        [field.key]: parseFloat(e.target.value) || field.defaultValue,
                      }))
                    }
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 transition"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-2">
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="w-full py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-medium rounded-lg text-sm transition-all disabled:opacity-50 shadow-lg shadow-violet-500/20"
            >
              {loading ? 'Generating…' : '⚡ Generate Geometry'}
            </button>
            <button
              onClick={handleSvgExport}
              disabled={!!exportLoading}
              className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-medium rounded-lg text-sm transition-all disabled:opacity-50"
            >
              {exportLoading === 'svg' ? 'Rendering…' : '🖼 Preview SVG'}
            </button>
            <button
              onClick={handlePdfExport}
              disabled={!!exportLoading}
              className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-medium rounded-lg text-sm transition-all disabled:opacity-50"
            >
              {exportLoading === 'pdf' ? 'Exporting…' : '📄 Download PDF'}
            </button>
          </div>
        </div>

        {/* Right: Canvas / Results */}
        <div className="flex-1 space-y-5 min-w-0">
          {error && (
            <div className="px-4 py-3 bg-red-950/60 border border-red-800 rounded-xl text-red-300 text-sm">
              {error}
            </div>
          )}

          {/* SVG Preview */}
          {svgContent && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-300">SVG Preview</h3>
                <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded">
                  {shapeLabel(selectedShape)}
                </span>
              </div>
              <div
                className="w-full bg-white rounded-lg overflow-hidden flex items-center justify-center"
                style={{ minHeight: 280 }}
                dangerouslySetInnerHTML={{ __html: svgContent }}
              />
            </div>
          )}

          {/* Geometry Result */}
          {result && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-300">Geometry Result</h3>
                <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2.5 py-1 rounded-full">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  {result.status}
                </span>
              </div>

              {/* Key metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                {[
                  { label: 'Shape', value: shapeLabel(result.shape_type as ShapeType) },
                  { label: 'Area', value: result.computed_area ? `${result.computed_area.toFixed(2)} in²` : '—' },
                  { label: 'Perimeter', value: result.computed_perimeter ? `${result.computed_perimeter.toFixed(2)} in` : '—' },
                  { label: 'Pieces', value: result.pieces.length },
                ].map((m) => (
                  <div key={m.label} className="bg-slate-800/60 rounded-lg px-3 py-2.5">
                    <p className="text-xs text-slate-500 mb-0.5">{m.label}</p>
                    <p className="text-white font-medium text-sm">{m.value}</p>
                  </div>
                ))}
              </div>

              {/* Pieces */}
              {result.pieces.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
                    Cut Pieces
                  </h4>
                  <div className="space-y-2">
                    {result.pieces.map((p) => (
                      <div
                        key={p.piece_id}
                        className="flex items-center justify-between bg-slate-800/40 rounded-lg px-3.5 py-2.5 text-sm"
                      >
                        <span className="text-slate-300 font-medium">{p.label}</span>
                        <span className="text-slate-500">
                          {p.length}" × {p.width}" — {p.area.toFixed(1)} in²
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* JSON accordion */}
              <details className="mt-5">
                <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-400 transition-colors">
                  View raw JSON response
                </summary>
                <pre className="mt-3 text-xs text-slate-400 bg-slate-950 rounded-lg p-4 overflow-auto max-h-64 border border-slate-800">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </details>
            </div>
          )}

          {/* Empty state */}
          {!result && !svgContent && !error && (
            <div className="flex-1 bg-slate-900 border border-slate-800 rounded-xl flex flex-col items-center justify-center py-20 text-center">
              <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mb-4 text-3xl">
                📐
              </div>
              <h3 className="text-white font-semibold mb-1">Ready to generate</h3>
              <p className="text-slate-500 text-sm max-w-xs">
                Select a surface type, set dimensions, and click{' '}
                <span className="text-violet-400">Generate Geometry</span> or{' '}
                <span className="text-slate-400">Preview SVG</span>.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
