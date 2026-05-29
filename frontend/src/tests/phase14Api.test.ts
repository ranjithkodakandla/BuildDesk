import { describe, it, expect, vi } from 'vitest';
import client from '../api/client';
import { projectsApi } from '../api/projects';
import { searchApi } from '../api/search';
import { tenantApi } from '../api/tenant';
import { UnitStatus, UnitVariant } from '../types/hierarchy';

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000/api/v1' },
  },
}));

describe('Phase 14 API clients', () => {
  it('unwraps hierarchy list responses', async () => {
    (client.get as any).mockResolvedValueOnce({ data: { projects: [{ project_id: 'p1' }] } });
    const projects = await projectsApi.listProjects();
    expect(projects).toEqual([{ project_id: 'p1' }]);
  });

  it('sends bulk unit updates', async () => {
    (client.put as any).mockResolvedValueOnce({ data: { updated_count: 12 } });
    const result = await projectsApi.bulkUpdateUnits('p1', {
      unit_ids: ['u1', 'u2'],
      unit_type_id: 'type-a',
      variant: UnitVariant.MIRROR,
      status: UnitStatus.ARCHIVED,
    });
    expect(client.put).toHaveBeenCalledWith('/projects/p1/units/bulk', {
      unit_ids: ['u1', 'u2'],
      unit_type_id: 'type-a',
      variant: 'MIR',
      status: 'archived',
    });
    expect(result.updated_count).toBe(12);
  });

  it('searches operational records', async () => {
    (client.post as any).mockResolvedValueOnce({ data: { results: [], total_count: 0 } });
    await searchApi.search({ entity_types: ['rfis'], status: 'open' });
    expect(client.post).toHaveBeenCalledWith('/search', { entity_types: ['rfis'], status: 'open' });
  });

  it('updates tenant profile metadata', async () => {
    (client.put as any).mockResolvedValueOnce({ data: { company_name: 'Canyon Surfaces' } });
    const result = await tenantApi.updateProfile({ company_name: 'Canyon Surfaces' });
    expect(client.put).toHaveBeenCalledWith('/tenant/profile', { company_name: 'Canyon Surfaces' });
    expect(result.company_name).toBe('Canyon Surfaces');
  });
});
