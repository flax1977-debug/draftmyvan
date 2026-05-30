import type { ProjectBuildStatus } from "../api";

// Bottom status strip, driven by GET /api/projects/{id}/build-status.

function Check({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={ok ? "text-emerald-400" : "text-amber-400"}>{ok ? "✓" : "⚠"}</span>
      {label}
    </span>
  );
}

export default function StatusBar({ status }: { status: ProjectBuildStatus | null }) {
  if (status === null) {
    return (
      <footer className="border-t border-neutral-800 bg-neutral-950 px-5 py-2 text-xs text-neutral-500">
        Checking build status…
      </footer>
    );
  }

  const boundsLabel = status.within_bounds
    ? "Within van bounds"
    : `${status.bounds_issues.length} out of bounds`;
  const collisionLabel =
    status.collision_count === 0 ? "No collisions" : `${status.collision_count} collision(s)`;
  const clearanceLabel =
    status.clearance_warnings.length === 0
      ? "No clearance warnings"
      : `${status.clearance_warnings.length} clearance warning(s)`;
  const payloadLabel = !status.limit_enforced
    ? `Weight ${status.total_weight_kg} kg (no limit)`
    : `Weight ${status.total_weight_kg}/${status.max_payload_kg} kg`;

  return (
    <footer className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-neutral-800 bg-neutral-950 px-5 py-2 text-xs text-neutral-400">
      <Check ok={status.within_bounds} label={boundsLabel} />
      <Check ok={status.collision_count === 0} label={collisionLabel} />
      <Check ok={status.clearance_warnings.length === 0} label={clearanceLabel} />
      <Check ok={status.payload_ok} label={payloadLabel} />
      <span className="text-neutral-600">
        not enforced: {status.clearance_not_enforced.join(", ") || "—"}
      </span>
      <span className="ml-auto font-medium">
        <Check ok={status.build_ready} label={status.build_ready ? "Build Ready" : "Not Ready"} />
      </span>
    </footer>
  );
}
