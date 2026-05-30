import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import StatusBar from "./components/StatusBar";
import VanOverviewPanel from "./components/VanOverviewPanel";
import ViewportPanel from "./components/ViewportPanel";
import CatalogPanel from "./components/CatalogPanel";

// Static app shell matching the target configurator layout. Data wiring
// (catalog, selected module, 3D viewport, build status) lands in the next task.
export default function App() {
  return (
    <div className="flex h-full w-full bg-neutral-950 text-neutral-200">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <div className="flex min-h-0 flex-1">
          <VanOverviewPanel />
          <ViewportPanel />
          <CatalogPanel />
        </div>
        <StatusBar />
      </div>
    </div>
  );
}
