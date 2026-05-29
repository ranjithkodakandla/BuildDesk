import React, { useState } from 'react';
import { importsApi, type ImportMapping, type ImportJobResponse, type ImportValidationPreviewResponse } from '../api/imports';

interface ImportModalProps {
  projectId: string;
  onClose: () => void;
}

export const ImportModal: React.FC<ImportModalProps> = ({ projectId, onClose }) => {
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<ImportJobResponse | null>(null);
  const [mapping, setMapping] = useState<ImportMapping>({
    unit_number_col: 'UnitNumber',
    unit_type_col: 'UnitType',
    building_col: 'Building',
    floor_col: 'Floor',
  });
  const [preview, setPreview] = useState<ImportValidationPreviewResponse | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await importsApi.uploadFile(projectId, file);
      setJob(data);
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!job || !file) return;
    setLoading(true);
    setError(null);
    try {
      await importsApi.updateMapping(projectId, job.job_id, mapping);
      const prev = await importsApi.validateImport(projectId, job.job_id, file);
      setPreview(prev);
    } catch (err: any) {
      setError(err.message || 'Validation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!job || !file) return;
    setLoading(true);
    setError(null);
    try {
      await importsApi.executeImport(projectId, job.job_id, file);
      onClose(); // Parent will refresh
    } catch (err: any) {
      setError(err.message || 'Execution failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto relative">
        <h2 className="text-xl font-bold mb-4">Import Units</h2>

        {error && <div className="bg-red-100 text-red-800 p-3 rounded mb-4 text-sm">{error}</div>}

        {!job && (
          <div className="space-y-4">
            <p className="text-gray-600">Upload a CSV file containing unit schedules.</p>
            <input type="file" accept=".csv" onChange={handleFileChange} className="block w-full" />
            <button
              onClick={handleUpload}
              disabled={!file || loading}
              className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
            >
              {loading ? 'Uploading...' : 'Upload & Continue'}
            </button>
          </div>
        )}

        {job && !preview && (
          <div className="space-y-4">
            <h3 className="font-semibold text-lg">Column Mapping</h3>
            <p className="text-sm text-gray-500">
              Map the columns from your CSV to the BuildDesk fields.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium">Unit Number Column *</label>
                <input
                  type="text"
                  value={mapping.unit_number_col || ''}
                  onChange={(e) => setMapping({ ...mapping, unit_number_col: e.target.value })}
                  className="w-full border rounded p-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium">Unit Type Column *</label>
                <input
                  type="text"
                  value={mapping.unit_type_col || ''}
                  onChange={(e) => setMapping({ ...mapping, unit_type_col: e.target.value })}
                  className="w-full border rounded p-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium">Building Column (Optional)</label>
                <input
                  type="text"
                  value={mapping.building_col || ''}
                  onChange={(e) => setMapping({ ...mapping, building_col: e.target.value })}
                  className="w-full border rounded p-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium">Floor Column (Optional)</label>
                <input
                  type="text"
                  value={mapping.floor_col || ''}
                  onChange={(e) => setMapping({ ...mapping, floor_col: e.target.value })}
                  className="w-full border rounded p-2"
                />
              </div>
            </div>
            
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={handleValidate}
                disabled={loading}
                className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
              >
                {loading ? 'Validating...' : 'Validate Import'}
              </button>
            </div>
          </div>
        )}

        {preview && (
          <div className="space-y-4">
            <h3 className="font-semibold text-lg">Validation Preview</h3>
            
            <div className="bg-gray-50 p-4 rounded border">
              <p>Total rows: <strong>{preview.total_rows}</strong></p>
              <p>Valid rows: <strong className="text-green-600">{preview.valid_rows}</strong></p>
              <p>Errors: <strong className="text-red-600">{preview.errors.length}</strong></p>
            </div>

            {preview.errors.length > 0 && (
              <div className="max-h-60 overflow-y-auto border border-red-200 rounded mt-4">
                <table className="w-full text-sm">
                  <thead className="bg-red-50 text-left">
                    <tr>
                      <th className="p-2 border-b">Row</th>
                      <th className="p-2 border-b">Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.errors.map((e, idx) => (
                      <tr key={idx} className="border-b last:border-0">
                        <td className="p-2">{e.row_index}</td>
                        <td className="p-2 text-red-600">{e.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex justify-end gap-2 mt-6 border-t pt-4">
              <button onClick={onClose} className="px-4 py-2 text-gray-600 hover:text-gray-900">
                Cancel
              </button>
              <button
                onClick={handleExecute}
                disabled={!preview.is_valid || loading}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? 'Executing...' : 'Execute Import'}
              </button>
            </div>
          </div>
        )}

        <div className="absolute top-4 right-4">
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-bold">
            &times;
          </button>
        </div>
      </div>
    </div>
  );
};
