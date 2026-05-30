import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Project } from '../types/hierarchy';
import { ProjectPackage, ProjectPackageStatus } from '../types/packages';
import { packagesApi } from '../api/packages';
import client from '../api/client';

interface Props {
  project: Project;
}

export const PackagesPanel: React.FC<Props> = ({ project }) => {
  const [pkg, setPkg] = useState<ProjectPackage | null>(null);
  const [history, setHistory] = useState<ProjectPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showGenModal, setShowGenModal] = useState(false);
  const [version, setVersion] = useState('Rev A');
  const [revisionNotes, setRevisionNotes] = useState('');

  // PDF blob state for embedded viewer
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const pdfBlobRef = useRef<string | null>(null);

  const revokePdfBlob = useCallback(() => {
    if (pdfBlobRef.current) {
      URL.revokeObjectURL(pdfBlobRef.current);
      pdfBlobRef.current = null;
    }
  }, []);

  const loadStatus = async () => {
    try {
      const hist = await packagesApi.listPackages(project.project_id);
      setHistory(hist);
      setPkg(hist.length > 0 ? hist[0] : null);
    } catch (e: unknown) {
      if ((e as { response?: { status?: number } })?.response?.status !== 404) {
        console.error(e);
      }
      setPkg(null);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadStatus(); }, [project.project_id]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (pkg?.status === ProjectPackageStatus.GENERATING) {
      interval = setInterval(loadStatus, 2000);
    }
    return () => { if (interval) clearInterval(interval); };
  }, [pkg?.status]);

  // Load PDF blob for embedded viewer
  const loadPdfPreview = useCallback(async (packageId?: string) => {
    setPdfLoading(true);
    revokePdfBlob();
    try {
      const path = packageId
        ? `/projects/${project.project_id}/packages/${packageId}/pdf`
        : `/projects/${project.project_id}/package/pdf`;
      const res = await client.get(path, { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const blobUrl = URL.createObjectURL(blob);
      pdfBlobRef.current = blobUrl;
      setPdfBlobUrl(blobUrl);
    } catch {
      setPdfBlobUrl(null);
    } finally {
      setPdfLoading(false);
    }
  }, [project.project_id, revokePdfBlob]);

  useEffect(() => () => revokePdfBlob(), [revokePdfBlob]);

  const ready = pkg?.status === ProjectPackageStatus.READY;
  const generating_bg = pkg?.status === ProjectPackageStatus.GENERATING;

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await packagesApi.generatePackage(project.project_id, { version, revision_notes: revisionNotes });
      setShowGenModal(false);
      setRevisionNotes('');
      setTimeout(loadStatus, 1500);
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(false);
    }
  };

  const openPdf = (packageId?: string) => {
    window.open(packagesApi.getPdfUrl(project.project_id, packageId), '_blank');
  };

  const statusConfig: Record<string, { bg: string; border: string; badge: string; dot: string }> = {
    [ProjectPackageStatus.READY]:             { bg: 'bg-green-50',  border: 'border-green-200',  badge: 'bg-green-100 text-green-800',  dot: 'bg-green-500' },
    [ProjectPackageStatus.GENERATING]:        { bg: 'bg-amber-50',  border: 'border-amber-200',  badge: 'bg-amber-100 text-amber-800',  dot: 'bg-amber-400' },
    [ProjectPackageStatus.DRAFT]:             { bg: 'bg-slate-50',  border: 'border-slate-200',  badge: 'bg-slate-100 text-slate-700',  dot: 'bg-slate-400' },
    [ProjectPackageStatus.GENERATION_FAILED]: { bg: 'bg-red-50',    border: 'border-red-200',    badge: 'bg-red-100 text-red-800',      dot: 'bg-red-500'   },
    [ProjectPackageStatus.ARCHIVED]:          { bg: 'bg-gray-50',   border: 'border-gray-200',   badge: 'bg-gray-100 text-gray-600',    dot: 'bg-gray-400'  },
  };

  const sc = pkg ? (statusConfig[pkg.status] || statusConfig[ProjectPackageStatus.READY]) : null;

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse max-w-5xl">
        <div className="h-40 bg-gray-100 rounded-xl" />
        <div className="h-64 bg-gray-100 rounded-xl" />
        <div className="h-40 bg-gray-100 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-5xl">

      {/* Package Status Control */}
      <section className={`rounded-xl border-2 shadow-sm p-6 ${sc ? `${sc.bg} ${sc.border}` : 'bg-white border-gray-200'}`}>
        <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Package Control</p>

        {!pkg ? (
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-gray-800 mb-1">No Package Generated</h3>
              <p className="text-sm text-gray-500">Generate the first fabrication package to create a PDF.</p>
            </div>
            <button
              onClick={() => setShowGenModal(true)}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow transition"
            >
              Generate Package
            </button>
          </div>
        ) : (
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className={`w-3 h-3 rounded-full ${sc?.dot} ${generating_bg ? 'animate-pulse' : ''}`} />
                <span className={`px-3 py-1 text-sm font-bold rounded-full ${sc?.badge}`}>
                  {pkg.status.replace(/_/g, ' ').toUpperCase()}
                </span>
                <span className="text-2xl font-black text-gray-900">{pkg.version}</span>
              </div>
              <div className="flex gap-5 text-sm text-gray-600">
                <span><span className="font-bold text-gray-800">{pkg.page_count ?? '—'}</span> pages</span>
                {pkg.generated_at && (
                  <span>Generated {new Date(pkg.generated_at).toLocaleString()}</span>
                )}
              </div>
              {generating_bg && (
                <p className="text-sm text-amber-700 mt-2 font-medium">⟳ Building PDF… this may take a moment</p>
              )}
            </div>
            <div className="flex gap-3 flex-wrap">
              {ready && (
                <>
                  <button
                    onClick={() => openPdf()}
                    className="px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white font-bold rounded-xl shadow transition"
                  >
                    Open PDF
                  </button>
                  <button
                    onClick={() => !pdfLoading && loadPdfPreview()}
                    disabled={pdfLoading}
                    className="px-5 py-2.5 border border-green-400 text-green-700 bg-white font-medium rounded-xl hover:bg-green-50 transition disabled:opacity-50"
                  >
                    {pdfLoading ? 'Loading preview…' : 'Preview PDF'}
                  </button>
                </>
              )}
              <button
                onClick={() => setShowGenModal(true)}
                className="px-5 py-2.5 border border-indigo-400 text-indigo-700 bg-white font-bold rounded-xl hover:bg-indigo-50 transition"
              >
                {pkg ? 'New Revision' : 'Generate'}
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Embedded PDF Preview */}
      {pdfBlobUrl && (
        <section className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <p className="text-sm font-bold text-gray-700">PDF Preview — {pkg?.version}</p>
            <button
              onClick={() => { revokePdfBlob(); setPdfBlobUrl(null); }}
              className="text-xs text-gray-400 hover:text-gray-700"
            >
              Close Preview
            </button>
          </div>
          <div style={{ height: 640 }}>
            <iframe
              src={pdfBlobUrl}
              title="Fabrication Package PDF"
              width="100%"
              height="100%"
              className="border-0"
            />
          </div>
        </section>
      )}

      {/* Revision History */}
      <section className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="px-6 py-4 border-b border-gray-100">
          <h3 className="font-bold text-gray-900">Revision History</h3>
          <p className="text-xs text-gray-400 mt-0.5">{history.length} package{history.length !== 1 ? 's' : ''} generated</p>
        </div>
        {history.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-400 text-sm">
            No revisions yet.
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {history.map((h, idx) => (
              <div key={h.package_id} className="px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="text-center min-w-[2rem]">
                    <p className="text-xs text-gray-400">{history.length - idx}</p>
                  </div>
                  <div>
                    <span className="font-bold text-gray-900">{h.version}</span>
                    {h.revision_notes && (
                      <span className="ml-2 text-sm text-gray-500">{h.revision_notes}</span>
                    )}
                    <p className="text-xs text-gray-400 mt-0.5">
                      {h.generated_at ? new Date(h.generated_at).toLocaleString() : '—'}
                      {h.page_count ? ` · ${h.page_count} pages` : ''}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                    h.status === ProjectPackageStatus.READY ? 'bg-green-100 text-green-700' :
                    h.status === ProjectPackageStatus.GENERATING ? 'bg-amber-100 text-amber-700' :
                    h.status === ProjectPackageStatus.GENERATION_FAILED ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {h.status.replace(/_/g, ' ')}
                  </span>
                  {h.status === ProjectPackageStatus.READY && (
                    <button
                      onClick={() => openPdf(h.package_id)}
                      className="text-sm text-indigo-600 hover:text-indigo-800 font-medium transition"
                    >
                      Download
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Generate Modal */}
      {showGenModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-lg font-bold text-gray-900 mb-1">
              {pkg ? 'Generate Revision' : 'Generate Package'}
            </h3>
            <p className="text-sm text-gray-500 mb-5">
              {pkg
                ? 'A new revision will be appended to the package history.'
                : 'This will compile all assemblies into a fabrication PDF.'}
            </p>

            <label className="block text-xs font-bold text-gray-600 mb-1">Version Label</label>
            <input
              type="text"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              className="border border-gray-300 w-full p-2.5 rounded-lg mb-4 text-sm"
              placeholder="Rev A"
            />

            <label className="block text-xs font-bold text-gray-600 mb-1">Revision Notes (optional)</label>
            <input
              type="text"
              value={revisionNotes}
              onChange={(e) => setRevisionNotes(e.target.value)}
              className="border border-gray-300 w-full p-2.5 rounded-lg mb-6 text-sm"
              placeholder="Updated kitchen dimensions"
            />

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowGenModal(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={generating || !version.trim()}
                className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg disabled:opacity-50 transition"
              >
                {generating ? 'Generating…' : 'Generate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
