// Top bar: project identity + global actions. The Build-Ready badge is a
// static placeholder here; it is wired to GET /api/build-status in a later task.

function Action({ label }: { label: string }) {
  return (
    <button
      type="button"
      className="rounded-md px-3 py-1.5 text-sm text-neutral-300 hover:bg-neutral-800"
    >
      {label}
    </button>
  );
}

export default function TopBar() {
  return (
    <header className="flex items-center justify-between border-b border-neutral-800 bg-neutral-900 px-5 py-3">
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold text-white">Sprinter L2H2</span>
        <span className="text-neutral-600">•</span>
        <span className="text-sm text-neutral-400">Weekend Explorer</span>
        <span className="ml-2 text-xs text-emerald-400">✓ Saved</span>
      </div>

      <div className="flex items-center gap-1">
        <Action label="↶ Undo" />
        <Action label="↷ Redo" />
        <Action label="Share" />
        <Action label="Export" />
        {/* Placeholder: replaced by a live build-status badge in a later task. */}
        <span className="ml-2 rounded-md bg-emerald-500 px-3 py-1.5 text-sm font-medium text-emerald-950">
          ✓ Build Ready
        </span>
      </div>
    </header>
  );
}
