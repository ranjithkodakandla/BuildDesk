import client from './client';

export type SearchEntityType = 'projects' | 'units' | 'assemblies' | 'packages' | 'rfis';

export interface SearchQueryRequest {
  query?: string;
  entity_types?: SearchEntityType[];
  project_id?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  building_id?: string;
  floor_id?: string;
  unit_type_id?: string;
  assembly_type?: string;
  limit?: number;
}

export interface SearchResultItem {
  id: string;
  entity_type: string;
  title: string;
  subtitle?: string;
  project_id: string;
  status?: string;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  results: SearchResultItem[];
  total_count: number;
}

export const searchApi = {
  search: async (body: SearchQueryRequest): Promise<SearchResponse> => {
    const res = await client.post('/search', body);
    return res.data;
  },
};
