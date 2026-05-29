export enum ProjectStatus {
  DRAFT = 'draft',
  ACTIVE = 'active',
  COMPLETED = 'completed',
  ON_HOLD = 'on_hold',
}

export interface HierarchyConfig {
  has_buildings: boolean;
  has_floors: boolean;
  has_unit_types: boolean;
}

export interface Project {
  project_id: string;
  name: string;
  client_name?: string;
  material?: string;
  issue_date?: string;
  description?: string;
  address?: string;
  status: ProjectStatus;
  hierarchy_config: HierarchyConfig;
  created_at: string;
}

export interface UnitType {
  unit_type_id: string;
  project_id: string;
  code: string;
  name: string;
  description?: string;
  is_mirror: boolean;
  is_ada: boolean;
  base_type_id?: string;
  sort_order: number;
}

export enum UnitVariant {
  STANDARD = 'standard',
  MIRROR = 'mirror',
  ADA = 'ada',
  LEFT = 'left',
  RIGHT = 'right',
  CUSTOM = 'custom',
}

export interface Unit {
  unit_id: string;
  project_id: string;
  building_id?: string;
  floor_id?: string;
  unit_type_id?: string;
  name: string;
  code: string;
  variant: UnitVariant;
  notes?: string;
  sort_order: number;
}
