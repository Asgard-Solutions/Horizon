import { LogOut } from "lucide-react";
import { api, post } from "../api";
import { useAuth } from "../App";
import { ErrorState, Loading, PageHeader } from "../components/States";
import { useAsync } from "../hooks";
import { LibrarySection } from "../settings/LibrarySection";
import { CollectionsSection } from "../settings/CollectionsSection";
import { NetworkSection } from "../settings/NetworkSection";
import type { SystemInfo } from "../types";

function DeviceSettings() {
  const { auth, refresh } = useAuth();
  return (
    <div className="page" data-testid="settings-page">
      <PageHeader title="Settings" />
      <section className="panel">
        <h2>This device</h2>
        <p>Paired as <strong>{auth.device_name}</strong>. Library folders and network settings can only be changed on the host PC.</p>
        <button className="btn btn--danger" data-autofocus onClick={() => post("/api/auth/logout").then(refresh)} data-testid="device-unpair-button">
          <LogOut size={22} /> Unpair this device
        </button>
      </section>
    </div>
  );
}

function HostSettings() {
  const { data, error, reload, setData } = useAsync(() => api<SystemInfo>("/api/system"), []);
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <Loading />;
  return (
    <div className="page" data-testid="settings-page">
      <PageHeader title="Settings" />
      <LibrarySection />
      <CollectionsSection />
      <NetworkSection system={data} onChange={setData} />
      <section className="panel" data-testid="settings-system">
        <h2>System</h2>
        <dl className="file-facts">
          <dt>Version</dt><dd>{data.version}</dd>
          <dt>Platform</dt><dd>{data.platform} · Python {data.python}</dd>
          <dt>Data folder</dt><dd data-testid="system-data-dir">{data.data_dir}</dd>
          <dt>FFprobe</dt>
          <dd data-testid="system-ffprobe">{data.ffprobe.path ? `${data.ffprobe.version ?? "found"} (${data.ffprobe.path})` : "Not found — codec inspection disabled. See README."}</dd>
        </dl>
      </section>
    </div>
  );
}

export default function Settings() {
  const { auth } = useAuth();
  return auth.role === "host" ? <HostSettings /> : <DeviceSettings />;
}
