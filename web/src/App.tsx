import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import StatusBar from "./components/StatusBar";
import VanOverviewPanel from "./components/VanOverviewPanel";
import ViewportPanel from "./components/ViewportPanel";
import CatalogPanel from "./components/CatalogPanel";
import {
  fetchBuildStatus,
  fetchModule,
  fetchModules,
  type BuildStatus,
  type ModuleCard,
  type ModuleDetail,
} from "./api";

// Configurator page: loads the catalog, selected-module detail, and build
// status from the API and threads them into the shell.
export default function App() {
  const [modules, setModules] = useState<ModuleCard[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ModuleDetail | null>(null);
  const [status, setStatus] = useState<BuildStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Initial load: catalog + build status.
  useEffect(() => {
    fetchModules()
      .then(({ modules }) => {
        setModules(modules);
        if (modules.length > 0) setSelectedId(modules[0].id);
      })
      .catch((e) => setError(String(e)));
    fetchBuildStatus()
      .then(setStatus)
      .catch((e) => setError(String(e)));
  }, []);

  // Selected-module detail follows the selection.
  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    fetchModule(selectedId)
      .then((d) => {
        if (!cancelled) setDetail(d);
      })
      .catch((e) => setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  return (
    <div className="flex h-full w-full bg-neutral-950 text-neutral-200">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar status={status} />
        {error && (
          <div className="bg-red-950/60 px-5 py-2 text-xs text-red-300">
            API error: {error} — is the backend running on the API origin?
          </div>
        )}
        <div className="flex min-h-0 flex-1">
          <VanOverviewPanel status={status} />
          <ViewportPanel detail={detail} />
          <CatalogPanel
            modules={modules}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </div>
        <StatusBar status={status} />
      </div>
    </div>
  );
}
