import { useMemo, useState } from "react";
import type { ModuleCard } from "../api";

// Right panel: module catalog from GET /api/modules, with a local category
// filter (derived from the modules' own types) and a text search. Clicking a
// card selects it for the inspector; ＋ Add places a new instance.

function dims(m: ModuleCard): string {
  const d = m.dimensions_mm;
  return `${d.width} × ${d.depth} × ${d.height} mm`;
}

function cap(s: string): string {
  return s.length ? s[0].toUpperCase() + s.slice(1) : s;
}

function matchesQuery(m: ModuleCard, q: string): boolean {
  if (!q.trim()) return true;
  const hay = [
    m.id,
    m.display_name ?? "",
    m.type,
    m.category ?? "",
    `${m.dimensions_mm.width}x${m.dimensions_mm.depth}x${m.dimensions_mm.height}`,
  ]
    .join(" ")
    .toLowerCase();
  return hay.includes(q.trim().toLowerCase());
}

function Card({
  module,
  selected,
  onSelect,
  onAdd,
}: {
  module: ModuleCard;
  selected: boolean;
  onSelect: (id: string) => void;
  onAdd: (module: ModuleCard) => void;
}) {
  const name = module.display_name ?? module.id;
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(module.id)}
      className={
        "w-full cursor-pointer rounded-lg border p-3 text-left transition-colors " +
        (selected
          ? "border-emerald-500 bg-emerald-500/10"
          : "border-neutral-800 bg-neutral-950 hover:border-neutral-700")
      }
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-medium text-neutral-100">{name}</span>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onAdd(module);
          }}
          className="rounded border border-emerald-600 px-2 py-0.5 text-xs text-emerald-400 hover:bg-emerald-500/15"
        >
          ＋ Add
        </button>
      </div>
      <div className="mt-1 text-xs text-neutral-500">{module.type}</div>
      <div className="mt-1 text-xs text-neutral-400">{dims(module)}</div>
      <div className="mt-1 flex justify-between text-xs">
        <span className="text-neutral-400">
          {module.weight_kg !== null ? `${module.weight_kg} kg` : "— kg"}
        </span>
        <span className="text-neutral-300">
          {module.cost_gbp !== null ? `£${module.cost_gbp}` : "—"}
        </span>
      </div>
    </div>
  );
}

export default function CatalogPanel({
  modules,
  selectedId,
  onSelect,
  onAdd,
}: {
  modules: ModuleCard[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAdd: (module: ModuleCard) => void;
}) {
  const [category, setCategory] = useState<string>("All");
  const [query, setQuery] = useState("");

  // Categories derived from the real catalog (no empty/fake categories).
  const categories = useMemo(() => {
    const types = Array.from(new Set(modules.map((m) => m.type))).sort();
    return ["All", ...types];
  }, [modules]);

  const filtered = useMemo(
    () =>
      modules.filter(
        (m) => (category === "All" || m.type === category) && matchesQuery(m, query),
      ),
    [modules, category, query],
  );

  return (
    <aside className="flex w-80 shrink-0 flex-col border-l border-neutral-800 bg-neutral-900">
      <div className="flex gap-4 border-b border-neutral-800 px-4 text-sm">
        <button type="button" className="border-b-2 border-emerald-400 py-3 font-medium text-emerald-400">
          Module Catalog
        </button>
        <button type="button" className="border-b-2 border-transparent py-3 text-neutral-500 hover:text-neutral-300">
          My Modules
        </button>
      </div>

      <div className="px-4 pt-3">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search modules…"
          className="w-full rounded-md border border-neutral-700 bg-neutral-950 px-3 py-1.5 text-sm text-neutral-200 placeholder:text-neutral-600 focus:border-emerald-500 focus:outline-none"
        />
      </div>

      <div className="flex flex-wrap gap-2 px-4 py-3">
        {categories.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setCategory(c)}
            className={
              "rounded-full px-3 py-1 text-xs " +
              (c === category
                ? "bg-emerald-500 font-medium text-emerald-950"
                : "bg-neutral-800 text-neutral-400 hover:text-neutral-200")
            }
          >
            {c === "All" ? "All" : cap(c)}
          </button>
        ))}
      </div>

      <div className="px-4 pb-1 text-xs text-neutral-500">
        {filtered.length} of {modules.length} modules
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto px-4 py-2">
        {modules.length === 0 ? (
          <p className="text-sm text-neutral-600">No modules found.</p>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-neutral-600">No modules match your filter.</p>
        ) : (
          filtered.map((m) => (
            <Card
              key={m.id}
              module={m}
              selected={m.id === selectedId}
              onSelect={onSelect}
              onAdd={onAdd}
            />
          ))
        )}
      </div>
    </aside>
  );
}
