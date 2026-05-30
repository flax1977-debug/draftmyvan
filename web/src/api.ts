// Typed client for the DraftMyVan FastAPI backend. Shapes mirror api/catalog.py
// and api/build_status.py. Fields the manifest schema does not yet carry come
// back as null and are rendered as "—" by the UI.

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export interface Dimensions {
  width: number;
  depth: number;
  height: number;
}

export interface ModuleCard {
  id: string;
  type: string;
  display_name: string | null;
  category: string | null;
  dimensions_mm: Dimensions;
  weight_kg: number | null;
  cost_gbp: number | null;
  glb_url: string;
  thumbnail_url: string | null;
  asset_present: boolean;
}

export interface ModuleDetail extends ModuleCard {
  anchor: string;
  placement: string;
  clearances: { front_mm: number; sides_mm: number; above_mm: number } | null;
  material_slots: string[] | null;
  collision_proxy: string | null;
  finish: string | null;
  plywood_thickness_mm: number | null;
  fusion_template: string | null;
  hardware: string[] | null;
  hardware_line_items: number | null;
  rules: {
    cnc_eligible?: boolean;
    build_difficulty?: string;
    service_access?: string[];
  } | null;
}

export interface BuildStatus {
  build_ready: boolean;
  all_valid: boolean;
  collisions: unknown[];
  collision_check_implemented: boolean;
  weight_ok: boolean;
  total_weight_kg: number;
  weight_limit_kg: number | null;
  module_count: number;
  missing_assets: number;
  schema_errors: Record<string, string[]>;
  package_errors: string[];
}

/** Prefix an API-relative path (e.g. a module's glb_url) with the API origin. */
export function assetUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function getJson<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`);
  if (!resp.ok) {
    throw new Error(`${path} → HTTP ${resp.status}`);
  }
  return (await resp.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error(`${path} → HTTP ${resp.status}`);
  }
  return (await resp.json()) as T;
}

export function fetchModules(): Promise<{ modules: ModuleCard[] }> {
  return getJson("/api/modules");
}

export function fetchModule(id: string): Promise<ModuleDetail> {
  return getJson(`/api/modules/${id}`);
}

export function fetchBuildStatus(): Promise<BuildStatus> {
  return getJson("/api/build-status");
}

// --- projects (Task 6/7 endpoints) -------------------------------------

export interface VanDimensions {
  length: number;
  width: number;
  height: number;
}

export interface Van {
  make: string | null;
  model: string | null;
  wheelbase_mm?: number | null;
  dimensions_mm: VanDimensions;
  max_payload_kg: number | null;
}

export interface ProjectInstanceModule {
  type: string;
  display_name: string | null;
  dimensions_mm: Dimensions;
  weight_kg: number | null;
  glb_url: string;
}

export interface ProjectInstance {
  instance_id: string;
  module_id: string;
  position_mm: { x: number; y: number; z: number };
  rotation_deg: number;
  zone: string;
  visible: boolean;
  module: ProjectInstanceModule | null;
}

export interface ProjectDetail {
  id: string;
  name: string;
  van: Van;
  module_instances: ProjectInstance[];
}

export interface Collision {
  instance_a: string;
  instance_b: string;
  overlap_mm: { x: number; y: number; z: number };
}

export interface ClearanceWarning {
  instance_a: string;
  instance_b: string;
  kind: string;
  gap_mm: number;
  required_mm: number;
}

export interface ProjectBuildStatus {
  project_id: string;
  instance_count: number;
  total_weight_kg: number;
  max_payload_kg: number | null;
  payload_headroom_kg: number | null;
  payload_ok: boolean;
  limit_enforced: boolean;
  within_bounds: boolean;
  bounds_issues: string[];
  collisions: Collision[];
  collision_count: number;
  clearance_warnings: ClearanceWarning[];
  clearance_not_enforced: string[];
  build_ready: boolean;
}

export function fetchProject(id: string): Promise<ProjectDetail> {
  return getJson(`/api/projects/${id}`);
}

export function fetchProjectBuildStatus(id: string): Promise<ProjectBuildStatus> {
  return getJson(`/api/projects/${id}/build-status`);
}

// Unsaved local edits: position/rotation overrides keyed by instance_id.
export interface InstanceEdit {
  instance_id: string;
  position_mm: { x: number; y: number; z: number };
  rotation_deg: number;
}

// Validate the saved project with local edits applied (server does not write).
export function validateLayout(
  id: string,
  instances: InstanceEdit[],
): Promise<ProjectBuildStatus> {
  return postJson(`/api/projects/${id}/validate-layout`, { instances });
}
