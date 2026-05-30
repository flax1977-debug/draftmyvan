// Left navigation rail. Static in this task; routing/active-state wiring
// comes later. "Layout" is shown as the active item to match the mockup.

const NAV_ITEMS = [
  "Dashboard",
  "Van Setup",
  "Layout",
  "Modules",
  "Materials",
  "Budget",
  "Build Plan",
  "Manufacture",
] as const;

const FOOTER_ITEMS = ["Settings", "Help"] as const;

const ACTIVE = "Layout";

export default function Sidebar() {
  return (
    <nav className="flex w-56 shrink-0 flex-col border-r border-neutral-800 bg-neutral-950 text-neutral-300">
      <div className="flex items-center gap-2 px-5 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
          ▣
        </div>
        <div>
          <div className="text-base font-semibold text-white">DraftMyVan</div>
          <div className="text-[11px] text-neutral-500">Design. Build. Adventure.</div>
        </div>
      </div>

      <ul className="mt-2 flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => {
          const active = item === ACTIVE;
          return (
            <li key={item}>
              <button
                type="button"
                className={
                  "w-full rounded-md px-3 py-2 text-left text-sm transition-colors " +
                  (active
                    ? "bg-emerald-500/15 font-medium text-emerald-400"
                    : "text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200")
                }
              >
                {item}
              </button>
            </li>
          );
        })}
      </ul>

      <ul className="space-y-1 border-t border-neutral-800 px-3 py-3">
        {FOOTER_ITEMS.map((item) => (
          <li key={item}>
            <button
              type="button"
              className="w-full rounded-md px-3 py-2 text-left text-sm text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200"
            >
              {item}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
