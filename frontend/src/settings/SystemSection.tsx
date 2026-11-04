import { api } from "../api";
import { useAsync } from "../hooks";
import type { MetadataStatus, ScanStatus, SystemInfo } from "../types";
import { getMotionPref } from "../theme/displayPrefs";
import { zoomSupported } from "../theme/uiScale";
import { SectionHead } from "./ui";

/** System information and diagnostics: what this install and this browser actually report. */
export function SystemSection({ system }: { system: SystemInfo | null }) {
  const meta = useAsync(() => api<MetadataStatus>("/api/metadata/status"), []);
  const scans = useAsync(() => (system ? api<ScanStatus>("/api/scans") : Promise.resolve(null)), [system]);
  const root = document.documentElement;
  const browser: [string, string][] = [
    ["Browser", navigator.userAgent],
    ["Window", `${window.innerWidth} × ${window.innerHeight} CSS px · display scaling ${Math.round(devicePixelRatio * 100)}%`],
    ["Interface size", `${Math.round(Number(root.dataset.uiScale ?? 1) * 100)}% · zoom ${zoomSupported() ? "supported" : "not supported"}`],
    ["Controller access", typeof navigator.getGamepads === "function" ? "Available (Gamepad API)" : "Not available"],
    ["Motion", `${getMotionPref() === "reduce" ? "Reduced (this device)" : "Follow system"} · system ${matchMedia("(prefers-reduced-motion: reduce)").matches ? "reduce" : "full"}`],
  ];
  const m = meta.data;
  const last = scans.data?.recent[0];
  return (
    <div className="ssection" data-testid="settings-system">
      <SectionHead title="System & diagnostics" intro="Everything runs on this PC. Nothing is sent to the internet." />
      {system && (
        <dl className="sfacts" tabIndex={0} data-nav data-testid="system-facts">
          <dt>Version</dt><dd data-testid="system-version">{system.version}</dd>
          <dt>Platform</dt><dd>{system.platform} · Python {system.python}</dd>
          <dt>Data folder</dt><dd data-testid="system-data-dir">{system.data_dir}</dd>
          <dt>FFprobe</dt>
          <dd data-testid="system-ffprobe">{system.ffprobe.path ? `${system.ffprobe.version ?? "found"} (${system.ffprobe.path})` : "Not found — codec inspection disabled. See README."}</dd>
          <dt>Last scan</dt><dd data-testid="system-last-scan">{last ? `${last.library_name}: ${last.state} · ${last.files_found} files` : "None since the server started"}</dd>
        </dl>
      )}
      {m && (
        <dl className="sfacts" tabIndex={0} data-nav data-testid="system-metadata">
          <dt>Media reader</dt>
          <dd>{m.available ? `${m.workers} workers · ${m.paused ? "paused" : "running"} · ${m.pending} pending · ${m.known} known · ${m.unknown} unreadable · ${m.unreachable} offline` : "Unavailable"}</dd>
        </dl>
      )}
      <h3 className="ssub">This browser</h3>
      <dl className="sfacts" tabIndex={0} data-nav data-testid="system-browser">{browser.map(([k, v]) => <div key={k} className="sfacts-pair"><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
    </div>
  );
}
