import client from './client';
import { Project, UnitStatus, UnitType, Unit, UnitVariant } from '../types/hierarchy';

export const projectsApi = {
  listProjects: async (): Promise<Project[]> => {
    const res = await client.get('/projects');
    const data = res.data;
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.projects)) return data.projects;
    return [];
  },
  getProject: async (projectId: string): Promise<Project> => {
    const res = await client.get(`/projects/${projectId}`);
    return res.data;
  },
  createProject: async (project: Omit<Project, 'project_id' | 'created_at'>): Promise<Project> => {
    const res = await client.post('/projects', project);
    return res.data;
  },
  listUnitTypes: async (projectId: string): Promise<UnitType[]> => {
    const res = await client.get(`/projects/${projectId}/unit-types`);
    return res.data.unit_types ?? res.data;
  },
  createUnitType: async (projectId: string, unitType: Partial<UnitType> & Pick<UnitType, 'code' | 'name'>): Promise<UnitType> => {
    const res = await client.post(`/projects/${projectId}/unit-types`, unitType);
    return res.data;
  },
  listUnits: async (projectId: string): Promise<Unit[]> => {
    const res = await client.get(`/projects/${projectId}/units`);
    return res.data.units ?? res.data;
  },
  createUnit: async (projectId: string, unit: Partial<Unit> & Pick<Unit, 'name' | 'code'>): Promise<Unit> => {
    const res = await client.post(`/projects/${projectId}/units`, unit);
    return res.data;
  },
  bulkCreateUnits: async (projectId: string, data: any): Promise<{ created_count: number, units: Unit[] }> => {
    const res = await client.post(`/projects/${projectId}/units/bulk`, data);
    return res.data;
  },
  bulkUpdateUnits: async (
    projectId: string,
    data: {
      unit_ids: string[];
      unit_type_id?: string;
      variant?: UnitVariant;
      status?: UnitStatus;
      building_id?: string;
      floor_id?: string;
    }
  ): Promise<{ updated_count: number }> => {
    const res = await client.put(`/projects/${projectId}/units/bulk`, data);
    return res.data;
  }
};
