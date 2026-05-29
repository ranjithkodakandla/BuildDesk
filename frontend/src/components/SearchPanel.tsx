import React, { useEffect, useState } from 'react';
import { SearchEntityType, SearchResultItem, searchApi } from '../api/search';

const STORAGE_KEY = 'bd_saved_search_filters';
const ENTITY_TYPES: SearchEntityType[] = ['projects', 'units', 'assemblies', 'packages', 'rfis'];

interface SavedFilter {
  name: string;
  query: string;
  entityTypes: SearchEntityType[];
  status: string;
}

interface Props {
  projectId?: string;
  onOpenProject?: (projectId: string) => void;
}

export const SearchPanel: React.FC<Props> = ({ projectId, onOpenProject }) => {
  const [query, setQuery] = useState('');
  const [entityTypes, setEntityTypes] = useState<SearchEntityType[]>(ENTITY_TYPES);
  const [status, setStatus] = useState('');
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [savedFilters, setSavedFilters] = useState<SavedFilter[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) setSavedFilters(JSON.parse(raw));
  }, []);

  const runSearch = async () => {
    setLoading(true);
    try {
      const data = await searchApi.search({
        query,
        entity_types: entityTypes,
        status: status || undefined,
        project_id: projectId,
        limit: 80,
      });
      setResults(data.results);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSearch().catch(console.error);
  }, [projectId]);

  const toggleType = (type: SearchEntityType) => {
    setEntityTypes((current) =>
      current.includes(type) ? current.filter((item) => item !== type) : [...current, type]
    );
  };

  const saveFilter = () => {
    const next = [
      ...savedFilters.filter((item) => item.name !== (query || 'Operational filter')),
      { name: query || 'Operational filter', query, entityTypes, status },
    ];
    setSavedFilters(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  };

  const applyFilter = (filter: SavedFilter) => {
    setQuery(filter.query);
    setEntityTypes(filter.entityTypes);
    setStatus(filter.status);
  };

  return (
    <section className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col md:flex-row gap-3">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search projects, units, packages, RFIs"
            className="border border-gray-300 rounded-md px-3 py-2 flex-1 text-sm"
          />
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
            <option value="">Any status</option>
            <option value="draft">Draft</option>
            <option value="in_progress">In progress</option>
            <option value="ready">Ready</option>
            <option value="submitted">Submitted</option>
            <option value="under_review">Under review</option>
            <option value="approved">Approved</option>
            <option value="open">Open RFI</option>
            <option value="archived">Archived</option>
          </select>
          <button onClick={runSearch} className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium">
            Search
          </button>
          <button onClick={saveFilter} className="border border-gray-300 px-4 py-2 rounded-md text-sm font-medium">
            Save
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {ENTITY_TYPES.map((type) => (
            <label key={type} className="inline-flex items-center gap-2 text-xs border border-gray-200 rounded px-2 py-1">
              <input
                type="checkbox"
                checked={entityTypes.includes(type)}
                onChange={() => toggleType(type)}
              />
              {type}
            </label>
          ))}
        </div>

        {savedFilters.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {savedFilters.map((filter) => (
              <button
                key={filter.name}
                onClick={() => applyFilter(filter)}
                className="text-xs border border-blue-200 text-blue-700 rounded px-2 py-1"
              >
                {filter.name}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="mt-5 border-t border-gray-100 pt-4">
        {loading ? (
          <p className="text-sm text-gray-500">Searching...</p>
        ) : results.length === 0 ? (
          <p className="text-sm text-gray-500">No matching operational records.</p>
        ) : (
          <div className="divide-y divide-gray-100">
            {results.map((result) => (
              <button
                key={`${result.entity_type}-${result.id}`}
                onClick={() => onOpenProject?.(result.project_id)}
                className="w-full text-left py-3 hover:bg-gray-50"
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-medium text-gray-900">{result.title}</p>
                    <p className="text-xs text-gray-500">{result.entity_type} {result.subtitle ? `· ${result.subtitle}` : ''}</p>
                  </div>
                  {result.status && <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">{result.status}</span>}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </section>
  );
};
