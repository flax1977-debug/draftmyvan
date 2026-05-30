// Right panel: module catalog with category filters and a "My Modules" tab.
// Card content is a static placeholder; it is populated from GET /api/modules
// in a later task.

const CATEGORIES = ["All", "Kitchen", "Storage", "Seating", "Bed", "Utilities"] as const;

export default function CatalogPanel() {
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

      <div className="flex flex-wrap gap-2 px-4 py-3">
        {CATEGORIES.map((c, i) => (
          <button
            key={c}
            type="button"
            className={
              "rounded-full px-3 py-1 text-xs " +
              (i === 0
                ? "bg-emerald-500 font-medium text-emerald-950"
                : "bg-neutral-800 text-neutral-400 hover:text-neutral-200")
            }
          >
            {c}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-2 text-sm text-neutral-600">
        Catalog loads here.
      </div>
    </aside>
  );
}
