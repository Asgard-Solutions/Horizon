import { Pause, Play, RotateCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, post } from "../../api";
import { useAsync } from "../../hooks";
import type { MetadataStatus } from "../../types";
import { ResourceStatus, SettingRow } from "../ui";

/** Background reading of media lengths (FFprobe, read-only). Pausing only delays it; nothing is lost. */
export function MetadataReader() {
  const { data, replaceData: setData, reload, error, loading } = useAsync(() => api<MetadataStatus>("/api/metadata/status"), []);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const inFlight = useRef(false);
  useEffect(() => {
    const t = window.setInterval(() => { if (!inFlight.current) reload(); }, 4000);
    return () => window.clearInterval(t);
  }, [reload]);
  const update = async (path: string, body?: unknown) => {
    if (inFlight.current) return;
    inFlight.current = true; setSaving(true); setSaveError(null);
    try { setData(await post<MetadataStatus>(path, body)); await reload(); }
    catch (e) { setSaveError((e as Error).message); }
    finally { inFlight.current = false; setSaving(false); }
  };
  const state = !data?.available ? "Unavailable — FFprobe was not found (see README)" : data.paused ? "Paused"
    : data.pending ? `Reading · ${data.pending.toLocaleString()} files left` : "Up to date";
  return (
    <section className="lm-meta" data-testid="metadata-reader">
      <ResourceStatus loading={loading && !data} error={error} onRetry={reload} testId="metadata-load" label="background reading status" />
      {saving && <p role="status" data-testid="metadata-save-status">Updating background reading…</p>}
      {saveError && <p className="form-error" role="alert" data-testid="metadata-save-error">Could not update background reading: {saveError}</p>}
      {data && <>
      <SettingRow label="Background media reading" testId="metadata-reader-row"
        hint={<>Reads each video's length in the background after a scan (files are opened read-only). <span data-testid="metadata-reader-state">{state}</span>.
          {` ${data.known.toLocaleString()} known · ${data.unknown} unreadable`}{data.unreachable ? ` · ${data.unreachable} waiting for an offline source` : ""}</>}>
        <div className="schoice-actions" data-nav-row>
          {data.available && (data.paused
            ? <button className="hbtn" aria-disabled={saving || undefined} onClick={() => update("/api/metadata/reader", { paused: false })} data-testid="metadata-resume-button"><Play size={20} /> Resume</button>
            : <button className="hbtn" aria-disabled={saving || undefined} onClick={() => update("/api/metadata/reader", { paused: true })} data-testid="metadata-pause-button"><Pause size={20} /> Pause</button>)}
          {data.available && data.unreachable > 0 && (
            <button className="hbtn hbtn--quiet" aria-disabled={saving || undefined} onClick={() => update("/api/metadata/retry")} data-testid="metadata-retry-button">
              <RotateCw size={20} /> Try offline files again
            </button>
          )}
        </div>
      </SettingRow>
      </>}
    </section>
  );
}
