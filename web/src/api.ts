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

export function fetchModules(): Promise<{ modules: ModuleCard[] }> {
  return getJson("/api/modules");
}

export function fetchModule(id: string): Promise<ModuleDetail> {
  return getJson(`/api/modules/${id}`);
}

export function fetchBuildStatus(): Promise<BuildStatus> {
  return getJson("/api/build-status");
}
