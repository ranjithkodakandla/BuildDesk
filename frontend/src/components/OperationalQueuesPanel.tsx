import React, { useEffect, useState } from 'react';
import { SearchResultItem, searchApi } from '../api/search';

interface Props {
  onOpenProject?: (projectId: string) => void;
}

export const OperationalQueuesPanel: React.FC<Props> = ({ onOpenProject }) => {
  const [rfis, setRfis] = useState<SearchResultItem[]>([]);
  const [packages, setPackages] = useState<SearchResultItem[]>([]);

  useEffect(() => {
    Promise.all([
      searchApi.search({ entity_types: ['rfis'], status: 'open', limit: 8 }),
      searchApi.search({ entity_types: ['packages'], status: 'submitted', limit: 8 }),
    ]).then(([rfiData, packageData]) => {
      setRfis(rfiData.results);
      setPackages(packageData.results);
    }).catch(console.error);
  }, []);

  const renderQueue = (title: string, items: SearchResultItem[]) => (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">{title}</h3>
        <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-gray-500">Queue clear.</p>
      ) : (
        <div className="divide-y divide-gray-100">
          {items.map((item) => (
            <button key={item.id} onClick={() => onOpenProject?.(item.project_id)} className="w-full py-3 text-left">
              <p className="text-sm font-medium text-gray-900">{item.title}</p>
              <p className="text-xs text-gray-500">{item.subtitle || item.status}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {renderQueue('Open RFIs', rfis)}
      {renderQueue('Packages Awaiting Approval', packages)}
    </section>
  );
};
