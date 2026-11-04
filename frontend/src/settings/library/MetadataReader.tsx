import { Pause, Play, RotateCw } from "lucide-react";
import { useEffect } from "react";
import { api, post } from "../../api";
import { useAsync } from "../../hooks";
import type { MetadataStatus } from "../../types";
import { SettingRow } from "../ui";

/** Background reading of media lengths (FFprobe, read-only). Pausing only delays it; nothing is lost. */
export function MetadataReader() {
  const { data, setData, reload } = useAsync(() => api<MetadataStatus>("/api/metadata/status"), []);
  useEffect(() => {
    const t = window.setInterval(() => reload(), 4000);
    return () => window.clearInterval(t);
  }, [reload]);
  if (!data) return null;
  const set = (paused: boolean) => post<MetadataStatus>("/api/metadata/reader", { paused }).then(setData);
  const state = !data.available ? "Unavailable — FFprobe was not found (see README)" : data.paused ? "Paused"
    : data.pending ? `Reading · ${data.pending.toLocaleString()} files left` : "Up to date";
  return (
    <section className="lm-meta" data-testid="metadata-reader">
      <SettingRow label="Background media reading" testId="metadata-reader-row"
        hint={<>Reads each video's length in the background after a scan (files are opened read-only). <span data-testid="metadata-reader-state">{state}</span>.
          {` ${data.known.toLocaleString()} known · ${data.unknown} unreadable`}{data.unreachable ? ` · ${data.unreachable} waiting for an offline source` : ""}</>}>
        <div className="schoice-actions" data-nav-row>
          {data.available && (data.paused
            ? <button className="hbtn" onClick={() => set(false)} data-testid="metadata-resume-button"><Play size={20} /> Resume</button>
            : <button className="hbtn" onClick={() => set(true)} data-testid="metadata-pause-button"><Pause size={20} /> Pause</button>)}
          {data.available && data.unreachable > 0 && (
            <button className="hbtn hbtn--quiet" onClick={() => post<MetadataStatus>("/api/metadata/retry").then(setData)} data-testid="metadata-retry-button">
              <RotateCw size={20} /> Try offline files again
            </button>
          )}
        </div>
      </SettingRow>
    </section>
  );
}
