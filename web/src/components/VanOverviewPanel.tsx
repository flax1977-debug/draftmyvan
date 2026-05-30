// Left panel: van overview, layout summary, and zones — all from the loaded
// project and its build status. Zones are derived from the actual placed
// instances; each instance is clickable to select it.

import type { ReactNode } from "react";
import type { ProjectBuildStatus, ProjectDetail, ProjectInstance } from "../api";

const ZONE_COLOR: Record<string, string> = {
  kitchen: "bg-emerald-400",
  seating: "bg-amber-400",
  storage: "bg-violet-400",
  bed: "bg-orange-400",
  utilities: "bg-sky-400",
};

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 text-sm">
      <span className="text-neutral-500">{label}</span>
      <span className="text-right text-neutral-200">{value}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="border-b border-neutral-800 px-4 py-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</h3>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function mm(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${value} mm`;
}

export default function VanOverviewPanel({
  project,
  status,
  selectedInstanceId,
  onSelectInstance,
}: {
  project: ProjectDetail | null;
  status: ProjectBuildStatus | null;
  selectedInstanceId: string | null;
  onSelectInstance: (instanceId: string) => void;
}) {
  const van = project?.van ?? null;
  const instances = project?.module_instances ?? [];

  // Group placed instances by zone, preserving the canonical zone order.
  const zoneOrder = ["kitchen", "seating", "storage", "bed", "utilities"];
  const byZone = new Map<string, ProjectInstance[]>();
  for (const inst of instances) {
    if (!byZone.has(inst.zone)) byZone.set(inst.zone, []);
    byZone.get(inst.zone)!.push(inst);
  }
  const zonesPresent = zoneOrder.filter((z) => byZone.has(z)).concat(
    [...byZone.keys()].filter((z) => !zoneOrder.includes(z)),
  );

  return (
    <aside className="w-64 shrink-0 overflow-y-auto border-r border-neutral-800 bg-neutral-900">
      <Section title="Van Overview">
        <Row label="Make" value={van?.make ?? "—"} />
        <Row label="Model" value={van?.model ?? "—"} />
        <Row label="Wheelbase" value={mm(van?.wheelbase_mm ?? null)} />
        <Row label="Length" value={mm(van?.dimensions_mm.length)} />
        <Row label="Width" value={mm(van?.dimensions_mm.width)} />
        <Row label="Height" value={mm(van?.dimensions_mm.height)} />
      </Section>

      <Section title="Layout Summary">
        <Row label="Total Modules" value={status ? String(status.instance_count) : "—"} />
        <Row label="Total Weight" value={status ? `${status.total_weight_kg} kg` : "—"} />
        <Row
          label="Payload"
          value={
            status && status.limit_enforced
              ? `${status.total_weight_kg}/${status.max_payload_kg} kg`
              : status
                ? "no limit"
                : "—"
          }
        />
        <Row label="Build Cost" value="—" />
        <Row label="Est. Build Time" value="—" />
      </Section>

      <Section title="Layout Zones">
        {instances.length === 0 ? (
          <p className="text-sm text-neutral-600">No placed modules.</p>
        ) : (
          zonesPresent.map((zone) => (
            <div key={zone} className="space-y-1">
              <div className="flex items-center gap-2 text-sm text-neutral-300">
                <span className={"h-2.5 w-2.5 rounded-full " + (ZONE_COLOR[zone] ?? "bg-neutral-400")} />
                <span className="capitalize">{zone}</span>
              </div>
              <ul className="ml-4 space-y-1">
                {byZone.get(zone)!.map((inst) => {
                  const selected = inst.instance_id === selectedInstanceId;
                  return (
                    <li key={inst.instance_id}>
                      <button
                        type="button"
                        onClick={() => onSelectInstance(inst.instance_id)}
                        className={
                          "w-full truncate rounded px-2 py-1 text-left text-xs " +
                          (selected
                            ? "bg-emerald-500/15 text-emerald-300"
                            : "text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200")
                        }
                      >
                        {inst.instance_id}
                        {!inst.visible && <span className="ml-1 text-neutral-600">(hidden)</span>}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))
        )}
      </Section>
    </aside>
  );
}
