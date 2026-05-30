import { useEffect, useMemo, useState } from "react";
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
  fetchProjectBuildStatus,
  type ModuleCard,
  type ModuleDetail,
  type ProjectBuildStatus,
  type ProjectDetail,
} from "./api";

const PROJECT_ID = "weekend_explorer";

type Selection = { kind: "module" | "instance"; id: string } | null;

export default function App() {
  const [modules, setModules] = useState<ModuleCard[]>([]);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [status, setStatus] = useState<ProjectBuildStatus | null>(null);
  const [selection, setSelection] = useState<Selection>(null);
  const [detail, setDetail] = useState<ModuleDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Initial load: catalog + the example project + its build status.
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
    fetchProjectBuildStatus(PROJECT_ID)
      .then(setStatus)
      .catch((e) => setError(String(e)));
  }, []);

  const selectedInstance = useMemo(() => {
    if (selection?.kind !== "instance" || !project) return null;
    return project.module_instances.find((i) => i.instance_id === selection.id) ?? null;
  }, [selection, project]);

  // Module detail is fetched for whichever module is in focus — a catalog
  // selection or the module behind a selected placed instance.
  const selectedModuleId =
    selection?.kind === "module" ? selection.id : selectedInstance?.module_id ?? null;

  useEffect(() => {
    if (!selectedModuleId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    fetchModule(selectedModuleId)
      .then((d) => {
        if (!cancelled) setDetail(d);
      })
      .catch((e) => setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [selectedModuleId]);

  return (
    <div className="flex h-full w-full bg-neutral-950 text-neutral-200">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar project={project} status={status} />
        {error && (
          <div className="bg-red-950/60 px-5 py-2 text-xs text-red-300">
            API error: {error} — is the backend running on the API origin?
          </div>
        )}
        <div className="flex min-h-0 flex-1">
          <VanOverviewPanel
            project={project}
            status={status}
            selectedInstanceId={selectedInstance?.instance_id ?? null}
            onSelectInstance={(id) => setSelection({ kind: "instance", id })}
          />
          <ViewportPanel project={project} detail={detail} instance={selectedInstance} />
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
