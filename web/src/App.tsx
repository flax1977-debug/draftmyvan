import { useEffect, useMemo, useRef, useState } from "react";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import StatusBar from "./components/StatusBar";
import VanOverviewPanel from "./components/VanOverviewPanel";
import ViewportPanel from "./components/ViewportPanel";
import CatalogPanel from "./components/CatalogPanel";
import {
  fetchModule,
  fetchModules,
  fetchProject,
  saveLayout,
  validateLayout,
  type InstanceFull,
  type ModuleCard,
  type ModuleDetail,
  type ProjectBuildStatus,
  type ProjectDetail,
  type ProjectInstance,
} from "./api";

const PROJECT_ID = "weekend_explorer";

type Selection = { kind: "module" | "instance"; id: string } | null;
type Edit = { position_mm: { x: number; y: number; z: number }; rotation_deg: number };

export default function App() {
  const [modules, setModules] = useState<ModuleCard[]>([]);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [status, setStatus] = useState<ProjectBuildStatus | null>(null);
  const [selection, setSelection] = useState<Selection>(null);
  const [detail, setDetail] = useState<ModuleDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  // Local, unsaved position/rotation overrides keyed by instance_id.
  const [edits, setEdits] = useState<Record<string, Edit>>({});
  // Local, unsaved instances added from the catalog (not yet in the project).
  const [added, setAdded] = useState<ProjectInstance[]>([]);
  const dirty = Object.keys(edits).length > 0 || added.length > 0;

  useEffect(() => {
    fetchModules()
      .then(({ modules }) => setModules(modules))
      .catch((e) => setError(String(e)));
    fetchProject(PROJECT_ID)
      .then((p) => {
        setProject(p);
        if (p.module_instances.length > 0) {
          setSelection({ kind: "instance", id: p.module_instances[0].instance_id });
        }
      })
      .catch((e) => setError(String(e)));
  }, []);

  // Apply local edits over the saved instances + locally-added instances.
  const effectiveInstances = useMemo<ProjectInstance[]>(() => {
    if (!project) return [];
    const apply = (inst: ProjectInstance) => {
      const e = edits[inst.instance_id];
      return e ? { ...inst, position_mm: { ...e.position_mm }, rotation_deg: e.rotation_deg } : inst;
    };
    return [...project.module_instances.map(apply), ...added.map(apply)];
  }, [project, edits, added]);

  const effectiveProject = useMemo<ProjectDetail | null>(
    () => (project ? { ...project, module_instances: effectiveInstances } : null),
    [project, effectiveInstances],
  );

  const selectedInstance = useMemo(() => {
    if (selection?.kind !== "instance") return null;
    return effectiveInstances.find((i) => i.instance_id === selection.id) ?? null;
  }, [selection, effectiveInstances]);

  const selectedModuleId =
    selection?.kind === "module" ? selection.id : selectedInstance?.module_id ?? null;

  useEffect(() => {
    if (!selectedModuleId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    fetchModule(selectedModuleId)
      .then((d) => !cancelled && setDetail(d))
      .catch((e) => setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [selectedModuleId]);

  // Live validation: re-run whenever the saved project loads or edits change.
  // Only the latest response is applied; on failure we keep the last status.
  const seq = useRef(0);
  useEffect(() => {
    if (!project) return;
    const instances: InstanceFull[] = effectiveInstances.map((i) => ({
      instance_id: i.instance_id,
      module_id: i.module_id,
      position_mm: i.position_mm,
      rotation_deg: i.rotation_deg,
      zone: i.zone,
      visible: i.visible,
    }));
    const mine = ++seq.current;
    validateLayout(PROJECT_ID, instances)
      .then((s) => {
        if (mine === seq.current) {
          setStatus(s);
          setEditError(null);
          setSaveError(null); // a new edit supersedes a prior failed save
        }
      })
      .catch((e) => {
        if (mine === seq.current) setEditError(String(e));
      });
  }, [project, effectiveInstances]);

  // --- local movement handlers (operate on the selected instance) ---------

  // Base edit for an instance: its current values from the saved project or
  // the locally-added list.
  function baseEdit(instanceId: string): Edit | null {
    const inst =
      project?.module_instances.find((i) => i.instance_id === instanceId) ??
      added.find((i) => i.instance_id === instanceId);
    if (!inst) return null;
    return { position_mm: { ...inst.position_mm }, rotation_deg: inst.rotation_deg };
  }

  function nudge(axis: "x" | "y", delta: number) {
    if (selection?.kind !== "instance") return;
    const id = selection.id;
    setEdits((prev) => {
      const base = prev[id] ?? baseEdit(id);
      if (!base) return prev;
      return {
        ...prev,
        [id]: { ...base, position_mm: { ...base.position_mm, [axis]: base.position_mm[axis] + delta } },
      };
    });
  }

  function rotate(delta: number) {
    if (selection?.kind !== "instance") return;
    const id = selection.id;
    setEdits((prev) => {
      const base = prev[id] ?? baseEdit(id);
      if (!base) return prev;
      return { ...prev, [id]: { ...base, rotation_deg: (((base.rotation_deg + delta) % 360) + 360) % 360 } };
    });
  }

  // Reset the selected instance: a locally-added (unsaved) instance is
  // removed entirely; a saved instance reverts to its saved position.
  function resetInstance() {
    if (selection?.kind !== "instance") return;
    const id = selection.id;
    const isAdded = added.some((i) => i.instance_id === id);
    setEdits((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    if (isAdded) {
      setAdded((prev) => prev.filter((i) => i.instance_id !== id));
      setSelection(null);
    }
  }

  function zoneForType(type: string): string {
    switch (type) {
      case "seating":
        return "seating";
      case "bed":
        return "bed";
      case "appliance":
      case "tank":
      case "panel":
        return "utilities";
      default:
        return "storage"; // cabinet, accessory, or unknown
    }
  }

  // Add a catalog module as a new local placed instance (unsaved).
  function addInstance(card: ModuleCard) {
    if (!project) return;
    const taken = new Set([...project.module_instances, ...added].map((i) => i.instance_id));
    let n = 2;
    let id = `${card.id}_${n}`;
    while (taken.has(id)) {
      n += 1;
      id = `${card.id}_${n}`;
    }
    // Default position: just behind the last instance in +Y (snapped, non-overlapping).
    let nextY = 0;
    for (const i of effectiveInstances) {
      const depth = i.module?.dimensions_mm.depth ?? 0;
      nextY = Math.max(nextY, i.position_mm.y + depth);
    }
    // Round UP to the 50 mm grid so the new instance clears the last one
    // (rounding down could land inside it and create a spurious collision).
    nextY = Math.ceil(nextY / 50) * 50;
    const inst: ProjectInstance = {
      instance_id: id,
      module_id: card.id,
      position_mm: { x: 0, y: nextY, z: 0 },
      rotation_deg: 0,
      zone: zoneForType(card.type),
      visible: true,
      module: {
        type: card.type,
        display_name: card.display_name,
        dimensions_mm: card.dimensions_mm,
        weight_kg: card.weight_kg,
        glb_url: card.glb_url,
      },
    };
    setAdded((prev) => [...prev, inst]);
    setSelection({ kind: "instance", id });
  }

  // Pointer drag in the 3D viewport feeds the SAME local edit state as the
  // nudge buttons (so validation/dirty/save are shared). No-op when the
  // snapped position is unchanged, to avoid redundant validation requests.
  function dragTo(instanceId: string, posMm: { x: number; y: number; z: number }) {
    setEdits((prev) => {
      const base = prev[instanceId] ?? baseEdit(instanceId);
      if (!base) return prev;
      const p = base.position_mm;
      if (p.x === posMm.x && p.y === posMm.y && p.z === posMm.z) return prev;
      return { ...prev, [instanceId]: { ...base, position_mm: posMm } };
    });
  }

  const selectedEdited =
    selection?.kind === "instance" ? selection.id in edits : false;

  // Persist the current effective layout, then rebaseline so dirty clears.
  async function save() {
    if (!effectiveProject) return;
    setSaving(true);
    setSaveError(null);
    const instances: InstanceFull[] = effectiveProject.module_instances.map((i) => ({
      instance_id: i.instance_id,
      module_id: i.module_id,
      position_mm: { ...i.position_mm },
      rotation_deg: i.rotation_deg,
      zone: i.zone,
      visible: i.visible,
    }));
    try {
      await saveLayout(PROJECT_ID, instances);
      const fresh = await fetchProject(PROJECT_ID);
      setProject(fresh);
      setEdits({}); // new baseline === saved; dirty clears
      setAdded([]); // added instances are now part of the saved project
    } catch (e) {
      setSaveError(String(e)); // keep local edits visible
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex h-full w-full bg-neutral-950 text-neutral-200">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          project={project}
          status={status}
          dirty={dirty}
          saving={saving}
          onSave={save}
        />
        {(error || saveError || editError) && (
          <div className="bg-red-950/60 px-5 py-2 text-xs text-red-300">
            {error
              ? `API error: ${error} — is the backend running on the API origin?`
              : saveError
                ? `Save failed: ${saveError} — your local edits are kept.`
                : `Validation failed: ${editError} — showing the last known layout.`}
          </div>
        )}
        <div className="flex min-h-0 flex-1">
          <VanOverviewPanel
            project={effectiveProject}
            status={status}
            selectedInstanceId={selectedInstance?.instance_id ?? null}
            onSelectInstance={(id) => setSelection({ kind: "instance", id })}
          />
          <ViewportPanel
            project={effectiveProject}
            detail={detail}
            instance={selectedInstance}
            edited={selectedEdited}
            onNudge={nudge}
            onRotate={rotate}
            onReset={resetInstance}
            onDrag={dragTo}
          />
          <CatalogPanel
            modules={modules}
            selectedId={selection?.kind === "module" ? selection.id : null}
            onSelect={(id) => setSelection({ kind: "module", id })}
            onAdd={addInstance}
          />
        </div>
        <StatusBar status={status} />
      </div>
    </div>
  );
}
