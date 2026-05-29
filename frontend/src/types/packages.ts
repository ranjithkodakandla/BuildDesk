export enum ProjectPackageStatus {
  DRAFT = 'draft',
  GENERATING = 'generating',
  READY = 'ready',
  GENERATION_FAILED = 'generation_failed',
  ARCHIVED = 'archived',
}

export interface PackageSummary {
  total_units: number;
  total_assemblies: number;
  total_parts: number;
  total_area_sqin: number;
  total_area_sqft: number;
  assembly_counts: Record<string, number>;
  unit_type_counts: Record<string, number>;
  part_counts_by_type: Record<string, number>;
}

export interface ProjectPackage {
  package_id: string;
  project_id: string;
  version: string;
  issued_by?: string;
  issued_date?: string;
  revision_notes?: string;
  status: ProjectPackageStatus;
  generated_at?: string;
  page_count: number;
}

export interface GeneratePackageRequest {
  version: string;
  issued_by?: string;
  revision_notes?: string;
}
