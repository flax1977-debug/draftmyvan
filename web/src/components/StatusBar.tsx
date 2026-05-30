// Bottom status strip. Static placeholders; wired to GET /api/build-status later.

const CHECKS = [
  "All modules valid",
  "No collisions detected",
  "Weight within limits",
] as const;

export default function StatusBar() {
  return (
    <footer className="flex items-center gap-4 border-t border-neutral-800 bg-neutral-950 px-5 py-2 text-xs text-neutral-400">
      {CHECKS.map((c) => (
        <span key={c} className="flex items-center gap-1.5">
          <span className="text-emerald-400">✓</span>
          {c}
        </span>
      ))}
    </footer>
  );
}
