import { UnitVariant } from './hierarchy';

export enum AssemblyType {
  KITCHEN = 'kitchen',
  VANITY = 'vanity',
  ISLAND = 'island',
  BAR_TOP = 'bar_top',
  LAUNDRY = 'laundry',
  DESK = 'desk',
  CUSTOM = 'custom',
}

export enum PartType {
  MAIN_TOP = 'main_top',
  LEFT_RETURN = 'left_return',
  RIGHT_RETURN = 'right_return',
  ISLAND_TOP = 'island_top',
  BAR_TOP = 'bar_top',
  APRON = 'apron',
  LOOSE_PIECE = 'loose_piece',
}

export enum EdgeType {
  EASED = 'eased',
  FLAT = 'flat',
  MITER = 'miter',
  LAMINATED = 'laminated',
  POLISHED = 'polished',
  RAW = 'raw',
  FINISHED = 'finished',
  UNFINISHED = 'unfinished',
  BULLNOSE = 'bullnose',
  HALF_BULLNOSE = 'half_bullnose',
  BEVEL = 'bevel',
  OGEE = 'ogee',
}

export enum CutoutType {
  SINK = 'sink',
  COOKTOP = 'cooktop',
  OUTLET = 'outlet',
  NOTCH = 'notch',
  GENERIC = 'generic',
}

export enum MountType {
  UNDERMOUNT = 'undermount',
  DROP_IN = 'drop_in',
  FARM_SINK = 'farm_sink',
  SURFACE_MOUNT = 'surface_mount',
  FLUSH_MOUNT = 'flush_mount',
  NONE = 'none',
}

export enum SplashType {
  BACKSPLASH = 'backsplash',
  LEFT_SPLASH = 'left_splash',
  RIGHT_SPLASH = 'right_splash',
  CUSTOM = 'custom',
}

export enum Position {
  FRONT = 'front',
  BACK = 'back',
  LEFT = 'left',
  RIGHT = 'right',
  CENTER = 'center',
  CUSTOM = 'custom',
}

export interface Dimensions {
  length: number;
  depth: number;
  thickness?: number;
}

export interface EdgeTreatment {
  edge_id?: string;
  part_id?: string;
  position: Position;
  edge_type: EdgeType;
  length?: number;
  notes?: string;
}

export interface Cutout {
  cutout_id?: string;
  part_id?: string;
  cutout_type: CutoutType;
  mount_type: MountType;
  dimensions: Dimensions;
  center_x: number;
  center_y: number;
  notes?: string;
}

export interface Hole {
  hole_id?: string;
  part_id?: string;
  diameter: number;
  center_x: number;
  center_y: number;
  purpose: string;
}

export interface Splash {
  splash_id?: string;
  part_id?: string;
  splash_type: SplashType;
  dimensions: Dimensions;
  notes?: string;
}

export interface Part {
  part_id?: string;
  assembly_id?: string;
  part_type: PartType;
  name: string;
  dimensions: Dimensions;
  notes?: string;
  edges: EdgeTreatment[];
  cutouts: Cutout[];
  holes: Hole[];
  splashes: Splash[];
}

export interface FabricationNote {
  note_id?: string;
  assembly_id?: string;
  content: string;
}

export interface Assembly {
  assembly_id?: string;
  project_id?: string;
  unit_id?: string;
  unit_type_id?: string;
  name: string;
  assembly_type: AssemblyType;
  variant: UnitVariant;
  parts: Part[];
  notes: FabricationNote[];
}
