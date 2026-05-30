// Left panel: van overview, layout summary, and zones. All values are static
// placeholders in this task; van/project data wiring comes later.

import type { ReactNode } from "react";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-neutral-500">{label}</span>
      <span className="text-neutral-200">{value}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="border-b border-neutral-800 px-4 py-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        {title}
      </h3>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

const ZONES = [
  { name: "Kitchen", color: "bg-emerald-400" },
  { name: "Seating", color: "bg-amber-400" },
  { name: "Storage", color: "bg-violet-400" },
  { name: "Bed", color: "bg-orange-400" },
  { name: "Utilities", color: "bg-sky-400" },
] as const;

export default function VanOverviewPanel() {
  return (
    <aside className="w-64 shrink-0 overflow-y-auto border-r border-neutral-800 bg-neutral-900">
      <Section title="Van Overview">
        <Row label="Make" value="Mercedes Sprinter" />
        <Row label="Wheelbase" value="— mm" />
        <Row label="Length" value="— mm" />
        <Row label="Width" value="— mm" />
        <Row label="Height" value="— mm" />
      </Section>

      <Section title="Layout Summary">
        <Row label="Total Modules" value="—" />
        <Row label="Total Weight" value="— kg" />
        <Row label="Build Cost" value="—" />
        <Row label="Est. Build Time" value="—" />
      </Section>

      <Section title="Layout Zones">
        {ZONES.map((z) => (
          <div key={z.name} className="flex items-center gap-2 text-sm text-neutral-300">
            <span className={"h-2.5 w-2.5 rounded-full " + z.color} />
            {z.name}
          </div>
        ))}
      </Section>
    </aside>
  );
}
