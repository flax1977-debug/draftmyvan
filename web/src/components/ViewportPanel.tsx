import { assetUrl, type ModuleDetail } from "../api";
import ModelViewer from "./ModelViewer";

// Center column: 2D/3D toggle, the GLB viewport, and the selected-module
// inspector. The "Selected Module" tab is wired to GET /api/modules/{id};
// the other tabs remain placeholders for later tasks.

const INSPECTOR_TABS = [
  "Selected Module",
  "Specifications",
  "Materials",
  "Hardware",
  "CNC Output",
] as const;

function Spec({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 text-sm">
      <span className="text-neutral-500">{label}</span>
      <span className="text-right text-neutral-200">{value}</span>
    </div>
  );
}

function Inspector({ detail }: { detail: ModuleDetail | null }) {
  if (detail === null) {
    return <div className="px-4 py-6 text-sm text-neutral-600">Select a module to see its details.</div>;
  }
  const d = detail.dimensions_mm;
  return (
    <div className="grid grid-cols-2 gap-x-8 gap-y-2 px-4 py-4">
      <Spec label="Name" value={detail.display_name ?? detail.id} />
      <Spec label="Type" value={detail.type} />
      <Spec label="Dimensions" value={`${d.width} × ${d.depth} × ${d.height} mm`} />
      <Spec label="Weight" value={detail.weight_kg !== null ? `${detail.weight_kg} kg` : "—"} />
      <Spec label="Anchor" value={detail.anchor} />
      <Spec label="Placement" value={detail.placement} />
      <Spec
        label="Material"
        value={detail.material_slots?.join(", ") ?? "—"}
      />
      <Spec label="Finish" value={detail.finish ?? "—"} />
      <Spec
        label="Plywood"
        value={detail.plywood_thickness_mm !== null ? `${detail.plywood_thickness_mm} mm` : "—"}
      />
      <Spec label="Cost" value={detail.cost_gbp !== null ? `£${detail.cost_gbp}` : "—"} />
      <Spec label="Hardware items" value={detail.hardware_line_items?.toString() ?? "—"} />
      <Spec label="Fusion template" value={detail.fusion_template ?? "—"} />
    </div>
  );
}

export default function ViewportPanel({ detail }: { detail: ModuleDetail | null }) {
  const glbUrl = detail && detail.asset_present ? assetUrl(detail.glb_url) : null;

  return (
    <main className="flex flex-1 flex-col bg-neutral-950">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="inline-flex overflow-hidden rounded-md border border-neutral-700 text-sm">
          <button type="button" className="bg-neutral-800 px-3 py-1 text-neutral-400">
            2D
          </button>
          <button type="button" className="bg-emerald-500 px-3 py-1 font-medium text-emerald-950">
            3D
          </button>
        </div>
        <button
          type="button"
          className="rounded-md border border-neutral-700 px-3 py-1 text-sm text-neutral-300 hover:bg-neutral-800"
        >
          ◳ Walkthrough
        </button>
      </div>

      <div className="mx-4 flex-1 overflow-hidden rounded-lg border border-neutral-800 bg-neutral-900/40">
        {glbUrl ? (
          <ModelViewer url={glbUrl} />
        ) : (
          <div className="flex h-full items-center justify-center text-neutral-600">
            {detail === null ? "Select a module to preview it in 3D." : "No asset available for this module."}
          </div>
        )}
      </div>

      <div className="mx-4 mt-4 mb-4 rounded-lg border border-neutral-800 bg-neutral-900">
        <div className="flex gap-4 border-b border-neutral-800 px-4 text-sm">
          {INSPECTOR_TABS.map((tab, i) => (
            <button
              key={tab}
              type="button"
              className={
                "border-b-2 py-2.5 " +
                (i === 0
                  ? "border-emerald-400 font-medium text-emerald-400"
                  : "border-transparent text-neutral-500 hover:text-neutral-300")
              }
            >
              {tab}
            </button>
          ))}
        </div>
        <Inspector detail={detail} />
      </div>
    </main>
  );
}
