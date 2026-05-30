// Center column: 2D/3D toggle, the viewport (a placeholder in this task; the
// react-three-fiber canvas loading the GLB arrives in a later task), and the
// selected-module inspector tabs.

const INSPECTOR_TABS = [
  "Selected Module",
  "Specifications",
  "Materials",
  "Hardware",
  "CNC Output",
] as const;

export default function ViewportPanel() {
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

      <div className="mx-4 flex flex-1 items-center justify-center rounded-lg border border-dashed border-neutral-700 bg-neutral-900/40 text-neutral-600">
        3D preview — viewport renders here
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
        <div className="px-4 py-6 text-sm text-neutral-600">
          Select a module to see its details.
        </div>
      </div>
    </main>
  );
}
