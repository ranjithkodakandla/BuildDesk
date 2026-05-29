import React, { useState, useEffect } from 'react';
import { exportsApi, type ExportType, type ExportFormat, type ExportJobResponse } from '../api/exports';

interface ExportModalProps {
  projectId: string;
  onClose: () => void;
}

const ExportModal: React.FC<ExportModalProps> = ({ projectId, onClose }) => {
  const [exportType, setExportType] = useState<ExportType>('schedule');
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [isExporting, setIsExporting] = useState(false);
  const [history, setHistory] = useState<ExportJobResponse[]>([]);

  useEffect(() => {
    loadHistory();
  }, [projectId]);

  const loadHistory = async () => {
    try {
      const jobs = await exportsApi.listExports(projectId);
      setHistory(jobs);
    } catch (err) {
      console.error('Failed to load export history', err);
    }
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      await exportsApi.requestExport(projectId, { export_type: exportType, format });
      await loadHistory();
    } catch (err) {
      console.error('Export failed', err);
      alert('Failed to request export');
    } finally {
      setIsExporting(false);
    }
  };

  const handleDownload = (job: ExportJobResponse) => {
    exportsApi.downloadExport(projectId, job.job_id, job.format).catch((err) => {
      console.error(err);
      alert('Export download failed');
    });
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col">
        <div className="p-6 border-b border-slate-800 flex justify-between items-center">
          <h2 className="text-xl font-bold text-white">Project Exports</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            ✕
          </button>
        </div>

        <div className="p-6 flex-1 overflow-y-auto">
          <div className="mb-8 bg-slate-800/50 p-6 rounded-lg border border-slate-700">
            <h3 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">New Export</h3>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Export Type</label>
                <select 
                  value={exportType}
                  onChange={(e) => setExportType(e.target.value as ExportType)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="schedule">Unit Schedule</option>
                  <option value="fabrication">Fabrication Parts</option>
                  <option value="summary">Project Summary</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Format</label>
                <select 
                  value={format}
                  onChange={(e) => setFormat(e.target.value as ExportFormat)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="csv">CSV (.csv)</option>
                  <option value="xlsx">Excel (.xlsx)</option>
                </select>
              </div>
            </div>
            <button
              onClick={handleExport}
              disabled={isExporting}
              className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded font-medium transition-colors"
            >
              {isExporting ? 'Generating Export...' : 'Generate Export'}
            </button>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">Recent Exports</h3>
            {history.length === 0 ? (
              <p className="text-slate-500 text-sm italic">No export history found.</p>
            ) : (
              <div className="space-y-3">
                {history.map(job => (
                  <div key={job.job_id} className="flex items-center justify-between bg-slate-800 p-3 rounded border border-slate-700">
                    <div>
                      <div className="text-sm font-medium text-white flex items-center gap-2">
                        <span className="uppercase text-xs bg-slate-700 px-2 py-0.5 rounded text-indigo-300">
                          {job.export_type}
                        </span>
                        <span>{job.format.toUpperCase()}</span>
                      </div>
                      <div className="text-xs text-slate-400 mt-1">
                        {new Date(job.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div>
                      {job.status === 'completed' ? (
                        <button
                          onClick={() => handleDownload(job)}
                          className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs font-medium rounded transition-colors"
                        >
                          Download
                        </button>
                      ) : (
                        <span className="text-xs text-slate-500 capitalize">{job.status}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="p-4 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-slate-600 hover:bg-slate-800 text-slate-300 rounded font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExportModal;
