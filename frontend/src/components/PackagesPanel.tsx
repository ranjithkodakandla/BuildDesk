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
  const [version, setVersion] = useState('1.0');

  const loadStatus = async () => {
    try {
      const data = await packagesApi.getPackageStatus(project.project_id);
      setPkg(data);
    } catch (e: any) {
      if (e.response?.status !== 404) {
        console.error(e);
      }
      setPkg(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, [project.project_id]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (pkg?.status === ProjectPackageStatus.GENERATING) {
      interval = setInterval(() => {
        loadStatus();
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [pkg?.status]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const data = await packagesApi.generatePackage(project.project_id, { version });
      setPkg(data);
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(false);
    }
  };

  const downloadPdf = () => {
    const url = packagesApi.getPdfUrl(project.project_id);
    window.open(url, '_blank');
  };

  if (loading) return <div>Loading package status...</div>;

  return (
    <div className="space-y-6">
      <section className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-lg font-bold mb-4">Fabrication Package</h2>
        
        {pkg ? (
          <div className="bg-gray-50 border p-4 rounded-lg flex justify-between items-center mb-6">
            <div>
              <p className="text-sm font-medium text-gray-500 uppercase">Current Package Status</p>
              <div className="mt-1 flex items-center space-x-3">
                <span className={`px-2 py-1 text-xs font-bold rounded uppercase ${
                  pkg.status === ProjectPackageStatus.READY ? 'bg-green-100 text-green-800' :
                  pkg.status === ProjectPackageStatus.GENERATING ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {pkg.status}
                </span>
                <span className="text-gray-900 font-bold">Version: {pkg.version}</span>
                <span className="text-gray-500 text-sm">| {pkg.page_count} Pages</span>
              </div>
              {pkg.generated_at && (
                <p className="text-xs text-gray-500 mt-2">Generated: {new Date(pkg.generated_at).toLocaleString()}</p>
              )}
            </div>
            
            {pkg.status === ProjectPackageStatus.READY && (
              <button onClick={downloadPdf} className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded font-bold shadow-sm">
                Download PDF
              </button>
            )}
          </div>
        ) : (
          <div className="bg-blue-50 border border-blue-100 p-4 rounded-lg mb-6">
            <p className="text-blue-800">No package has been generated for this project yet.</p>
          </div>
        )}

        <div className="border-t pt-6 mt-6">
          <h3 className="text-md font-bold mb-3">Generate New Package</h3>
          <p className="text-sm text-gray-600 mb-4">
            Generating a new package will snapshot the current project hierarchy and assemblies into an immutable multi-page PDF document.
          </p>
          
          <div className="flex space-x-3 items-end">
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Version string</label>
              <input 
                type="text" 
                value={version}
                onChange={e => setVersion(e.target.value)}
                className="border p-2 rounded w-48"
              />
            </div>
            <button 
              onClick={handleGenerate} 
              disabled={generating}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded font-bold disabled:opacity-50"
            >
              {generating ? 'Generating...' : 'Generate Package'}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};
