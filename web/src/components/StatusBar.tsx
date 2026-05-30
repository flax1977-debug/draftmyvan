import type { BuildStatus } from "../api";

// Bottom status strip, driven by GET /api/build-status. Checks that are not
// yet implemented are labelled as such rather than shown as a clean pass.

function Check({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={ok ? "text-emerald-400" : "text-amber-400"}>{ok ? "✓" : "⚠"}</span>
      {label}
    </span>
  );
}

export default function StatusBar({ status }: { status: BuildStatus | null }) {
  if (status === null) {
    return (
      <footer className="border-t border-neutral-800 bg-neutral-950 px-5 py-2 text-xs text-neutral-500">
        Checking build status…
      </footer>
    );
  }

  const collisionsLabel = status.collision_check_implemented
    ? status.collisions.length === 0
      ? "No collisions detected"
      : `${status.collisions.length} collision(s)`
    : "Collision check not implemented";

  const weightLabel =
    status.weight_limit_kg === null
      ? `Weight ${status.total_weight_kg} kg (no limit set)`
      : `Weight ${status.total_weight_kg}/${status.weight_limit_kg} kg`;

  return (
    <footer className="flex items-center gap-4 border-t border-neutral-800 bg-neutral-950 px-5 py-2 text-xs text-neutral-400">
      <Check ok={status.all_valid} label={status.all_valid ? "All modules valid" : "Validation errors"} />
      <Check ok={status.collision_check_implemented && status.collisions.length === 0} label={collisionsLabel} />
      <Check ok={status.weight_ok} label={weightLabel} />
    </footer>
  );
}
