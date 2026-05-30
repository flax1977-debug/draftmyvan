import type { ProjectBuildStatus, ProjectDetail } from "../api";

// Top bar: project identity + global actions + a live Build-Ready badge
// (driven by the project's build status).

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

function BuildBadge({ status }: { status: ProjectBuildStatus | null }) {
  if (status === null) {
    return (
      <span className="ml-2 rounded-md bg-neutral-700 px-3 py-1.5 text-sm font-medium text-neutral-300">
        Checking…
      </span>
    );
  }
  if (status.build_ready) {
    return (
      <span className="ml-2 rounded-md bg-emerald-500 px-3 py-1.5 text-sm font-medium text-emerald-950">
        ✓ Build Ready
      </span>
    );
  }
  return (
    <span className="ml-2 rounded-md bg-amber-500 px-3 py-1.5 text-sm font-medium text-amber-950">
      ⚠ Not Ready
    </span>
  );
}

export default function TopBar({
  project,
  status,
  dirty,
  saving,
  onSave,
}: {
  project: ProjectDetail | null;
  status: ProjectBuildStatus | null;
  dirty: boolean;
  saving: boolean;
  onSave: () => void;
}) {
  const vanLabel = project?.van.model ?? null;
  return (
    <header className="flex items-center justify-between border-b border-neutral-800 bg-neutral-900 px-5 py-3">
      <div className="flex items-center gap-3">
        {vanLabel && <span className="text-sm font-semibold text-white">{vanLabel}</span>}
        {vanLabel && <span className="text-neutral-600">•</span>}
        <span className="text-sm text-neutral-300">{project?.name ?? "—"}</span>
        {dirty ? (
          <span className="ml-2 text-xs text-amber-400">● Unsaved changes</span>
        ) : (
          <span className="ml-2 text-xs text-emerald-400">✓ Saved</span>
        )}
      </div>

      <div className="flex items-center gap-1">
        <Action label="↶ Undo" />
        <Action label="↷ Redo" />
        <Action label="Share" />
        <Action label="Export" />
        <button
          type="button"
          onClick={onSave}
          disabled={!dirty || saving}
          className={
            "ml-2 rounded-md px-3 py-1.5 text-sm font-medium " +
            (!dirty || saving
              ? "cursor-not-allowed bg-neutral-800 text-neutral-500"
              : "bg-sky-500 text-sky-950 hover:bg-sky-400")
          }
        >
          {saving ? "Saving…" : "Save"}
        </button>
        <BuildBadge status={status} />
      </div>
    </header>
  );
}
