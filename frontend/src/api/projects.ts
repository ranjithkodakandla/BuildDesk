import client from './client';
import { Project, UnitType, Unit } from '../types/hierarchy';

export const projectsApi = {
  listProjects: async (): Promise<Project[]> => {
    const res = await client.get('/projects');
    return res.data;
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
    return res.data;
  },
  createUnitType: async (projectId: string, unitType: Omit<UnitType, 'unit_type_id' | 'project_id'>): Promise<UnitType> => {
    const res = await client.post(`/projects/${projectId}/unit-types`, unitType);
    return res.data;
  },
  listUnits: async (projectId: string): Promise<Unit[]> => {
    const res = await client.get(`/projects/${projectId}/units`);
    return res.data;
  },
  createUnit: async (projectId: string, unit: Omit<Unit, 'unit_id' | 'project_id'>): Promise<Unit> => {
    const res = await client.post(`/projects/${projectId}/units`, unit);
    return res.data;
  }
};
