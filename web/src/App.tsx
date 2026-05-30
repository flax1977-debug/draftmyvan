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
  type InstanceEdit,
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
  const dirty = Object.keys(edits).length > 0;

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

  // Apply local edits over the saved instances for rendering + inspection.
  const effectiveInstances = useMemo<ProjectInstance[]>(() => {
    if (!project) return [];
    return project.module_instances.map((inst) => {
      const e = edits[inst.instance_id];
      return e ? { ...inst, position_mm: { ...e.position_mm }, rotation_deg: e.rotation_deg } : inst;
    });
  }, [project, edits]);

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
    const overrides: InstanceEdit[] = Object.entries(edits).map(([instance_id, e]) => ({
      instance_id,
      position_mm: e.position_mm,
      rotation_deg: e.rotation_deg,
    }));
    const mine = ++seq.current;
    validateLayout(PROJECT_ID, overrides)
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
  }, [project, edits]);

  // --- local movement handlers (operate on the selected instance) ---------

  // Base edit for an instance: its current override, or its saved values.
  function baseEdit(instanceId: string): Edit | null {
    const saved = project?.module_instances.find((i) => i.instance_id === instanceId);
    if (!saved) return null;
    return { position_mm: { ...saved.position_mm }, rotation_deg: saved.rotation_deg };
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

  function resetInstance() {
    if (selection?.kind !== "instance") return;
    setEdits((prev) => {
      const next = { ...prev };
      delete next[selection.id];
      return next;
    });
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
          />
        </div>
        <StatusBar status={status} />
      </div>
    </div>
  );
}
