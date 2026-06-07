// Template-driven fabrication API types (Phase 4 backend)

export interface UIFieldSpec {
  key: string;
  label: string;
  field_type: 'number' | 'boolean' | 'select';
  visible: boolean;
  required: boolean;
  unit?: string | null;
  options?: string[] | null;
  hint?: string | null;
}

export interface TemplateUIContract {
  template_id: string;
  display_name: string;
  category: string;
  dimension_term: string; // "Width" | "Length"
  fields: UIFieldSpec[];
}

export interface TemplateDefinition {
  id: string;
  category: 'kitchen' | 'vanity' | 'island';
  display_name: string;
  description: string;
  defaults: Record<string, unknown>;
  editable_fields: string[];
  supported_features: string[];
}

export interface TemplateDetail {
  definition: TemplateDefinition;
  ui_contract: TemplateUIContract;
}

// ─── Builder config — the installer-facing state object ────────────────────

export interface SplashConfig {
  back: boolean;
  left: boolean;
  right: boolean;
  height: number;
}

export interface SinkConfig {
  type: 'rectangle' | 'oval' | 'none';
  position: 'center' | 'left' | 'right';
  size: 'small' | 'standard' | 'large';
}

export interface BuilderConfig {
  template_id: string;
  name: string;
  width: number;
  depth: number;
  thickness: number;
  mirror: boolean;
  edge_finish: 'polished' | 'eased' | 'miter' | 'flat';
  splash: SplashConfig;
  sink: SinkConfig;
}

// ─── API request shape ──────────────────────────────────────────────────────

export interface TemplateGenerateRequest {
  template_id: string;
  name?: string;
  project_id?: string;
  width: number;
  depth: number;
  thickness?: number;
  mirror?: boolean;
  edge_finish?: string;
  splash?: SplashConfig;
  sink?: SinkConfig;
}

// ─── API response shapes ────────────────────────────────────────────────────

export interface AssemblyPartResponse {
  part_id: string;
  part_type: string;
  name: string;
  length: number;
  depth: number;
  thickness?: number;
  cutout_count: number;
  splash_count: number;
}

export interface AssemblyGenerateResponse {
  assembly_id: string;
  template_id: string;
  name: string;
  assembly_type: string;
  variant: string;
  part_count: number;
  parts: AssemblyPartResponse[];
  warnings: string[];
}
