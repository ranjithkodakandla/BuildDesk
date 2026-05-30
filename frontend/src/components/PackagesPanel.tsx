import React, { useEffect, useState } from 'react';
import { Project } from '../types/hierarchy';
import { ProjectPackage, ProjectPackageStatus } from '../types/packages';
import { packagesApi } from '../api/packages';

interface Props {
  project: Project;
}

export const PackagesPanel: React.FC<Props> = ({ project }) => {
  const [pkg, setPkg] = useState<ProjectPackage | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [version, setVersion] = useState('Rev A');
  const [revisionNotes, setRevisionNotes] = useState('');
  const [history, setHistory] = useState<ProjectPackage[]>([]);

  const loadStatus = async () => {
    try {
      const data = await packagesApi.getPackageStatus(project.project_id);
      setPkg(data);
      const hist = await packagesApi.listPackages(project.project_id);
      setHistory(hist);
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

  useEffect(() => {
    loadStatus();
  }, [project.project_id]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (pkg?.status === ProjectPackageStatus.GENERATING) {
      interval = setInterval(loadStatus, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [pkg?.status]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await packagesApi.generatePackage(project.project_id, { version, revision_notes: revisionNotes });
      setShowModal(false);
      setRevisionNotes('');
      setTimeout(loadStatus, 1500);
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(false);
    }
  };

  const downloadPdf = (packageId?: string) => {
    window.open(packagesApi.getPdfUrl(project.project_id, packageId), '_blank');
  };

  if (loading) return <div>Loading package…</div>;

  const ready = pkg?.status === ProjectPackageStatus.READY;

  return (
    <div className="space-y-6">
      <section className="bg-white p-8 rounded-xl border border-gray-200 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-widest text-gray-400 mb-2">Package Status</p>

        {pkg ? (
          <div className="flex flex-wrap items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span
                  className={`px-3 py-1 text-sm font-bold rounded uppercase ${
                    ready ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}
                >
                  {pkg.status}
                </span>
                <span className="text-2xl font-bold text-gray-900">{pkg.version}</span>
              </div>
              <p className="text-gray-600">{pkg.page_count || '—'} pages</p>
              {pkg.generated_at && (
                <p className="text-sm text-gray-500 mt-1">
                  Generated: {new Date(pkg.generated_at).toLocaleString()}
                </p>
              )}
            </div>
            <div className="flex gap-3">
              {ready && (
                <button
                  onClick={() => downloadPdf()}
                  className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-bold"
                >
                  Download PDF
                </button>
              )}
              <button
                onClick={() => setShowModal(true)}
                className="border border-indigo-600 text-indigo-700 px-6 py-3 rounded-lg font-bold hover:bg-indigo-50"
              >
                Generate Revision
              </button>
            </div>
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-500 mb-4">No fabrication package generated yet.</p>
            <button
              onClick={() => setShowModal(true)}
              className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-bold"
            >
              Generate Package
            </button>
          </div>
        )}

        {ready && (
          <div className="mt-6 border rounded-lg overflow-hidden bg-gray-50 h-48 flex items-center justify-center">
            <p className="text-sm text-gray-500">PDF preview — use Download PDF to open full package</p>
          </div>
        )}
      </section>

      <section className="bg-white p-6 rounded-xl border border-gray-200">
        <h3 className="font-bold text-gray-900 mb-4">Revision History</h3>
        {history.length === 0 ? (
          <p className="text-sm text-gray-400">No revisions yet</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {history.map((h) => (
              <li key={h.package_id} className="py-3 flex justify-between items-center">
                <div>
                  <span className="font-semibold">{h.version}</span>
                  <span className="ml-3 text-xs uppercase text-gray-500">{h.status}</span>
                </div>
                {h.status === ProjectPackageStatus.READY && (
                  <button
                    onClick={() => downloadPdf(h.package_id)}
                    className="text-indigo-600 text-sm font-medium"
                  >
                    Download
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h3 className="text-lg font-bold mb-4">Generate Revision</h3>
            <label className="block text-xs font-bold text-gray-600 mb-1">Version</label>
            <input
              type="text"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              className="border w-full p-2 rounded mb-4"
            />
            <label className="block text-xs font-bold text-gray-600 mb-1">Notes (optional)</label>
            <input
              type="text"
              value={revisionNotes}
              onChange={(e) => setRevisionNotes(e.target.value)}
              className="border w-full p-2 rounded mb-6"
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 rounded border">
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="px-4 py-2 rounded bg-indigo-600 text-white font-bold disabled:opacity-50"
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
