import { HardDrive, Network, RefreshCw, Trash2 } from "lucide-react";
import type { Library, ScanJob } from "../../types";
import { fmtBytes, fmtWhen } from "../ui";

const RESULT: Record<string, string> = {
  complete: "Last scan completed", partial: "Last scan finished with warnings", cancelled: "Last scan was cancelled — nothing was removed",
  unreachable: "Last scan could not reach this source — nothing was removed", failed: "Last scan failed — nothing was removed",
};

function status(lib: Library, job: ScanJob | undefined) {
  if (job?.state === "running") return { tone: "busy", text: "Scanning now" };
  if (job?.state === "queued") return { tone: "busy", text: "Waiting to scan" };
  if (!lib.reachable) return { tone: "warn", text: lib.network ? "Network source not reachable" : "Folder not reachable" };
  return { tone: "ok", text: "Available" };
}

/** One media source: what it holds, whether it is reachable, how its last scan went, and its actions. */
export function SourceRow({ lib, job, pending, onRescan, onRemove }: { lib: Library; job?: ScanJob; pending?: boolean; onRescan: () => void; onRemove: () => void }) {
  const st = status(lib, job);
  const s = lib.last_scan_summary;
  const Icon = lib.network ? Network : HardDrive;
  return (
    <article className={`lm-source lm-source--${st.tone}`} data-testid={`library-item-${lib.id}`}>
      <Icon size={30} className="lm-source-icon" aria-hidden="true" />
      <div className="lm-source-body">
        <div className="lm-source-title">
          <strong>{lib.name}</strong>
          <span className={`lm-pill lm-pill--${st.tone}`} data-testid={`library-status-${lib.id}`}>{st.text}</span>
          <span className="lm-pill">{lib.network ? "Network" : "Local"}</span>
        </div>
        <code data-testid={`library-path-${lib.id}`}>{lib.path}</code>
        <span className="lm-facts" data-testid={`library-counts-${lib.id}`}>
          {lib.counts.movies} movies · {lib.details.shows} series · {lib.counts.episodes} episodes · {fmtBytes(lib.details.size_bytes)}
          {lib.details.metadata_pending > 0 && ` · ${lib.details.metadata_pending} lengths still to read`}
        </span>
        <span className="lm-facts" data-testid={`library-last-success-${lib.id}`}>Last successful scan: {fmtWhen(lib.last_success_at)}</span>
        {!lib.reachable && !job && (
          <p className="lm-note" data-testid={`library-unreachable-note-${lib.id}`}>
            Its titles stay in your library and watch history is kept. Check that the {lib.network ? "NAS is on and the share opens in File Explorer" : "drive is connected"}, then rescan.
          </p>
        )}
        {s?.status && s.status !== "complete" && (
          <details className="lm-result" data-testid={`library-scan-result-${lib.id}`}>
            <summary>{RESULT[s.status] ?? "Last scan"} · {fmtWhen(s.finished_at)}</summary>
            <ul>{s.errors.slice(0, 8).map((e) => <li key={e}>{e}</li>)}</ul>
          </details>
        )}
        {s?.status === "complete" && (
          <span className="lm-facts lm-facts--quiet" data-testid={`library-scan-summary-${lib.id}`}>
            Last scan: {s.files_found} videos · {s.added} new · {s.updated} changed · {s.removed} removed
          </span>
        )}
      </div>
      <div className="lm-source-actions" data-nav-row>
        {/* Stays focusable while busy (a disabled button would drop controller focus). */}
        <button className="hbtn" onClick={() => !job && !pending && onRescan()} aria-disabled={!!job || pending || undefined} data-testid={`library-rescan-button-${lib.id}`}>
          <RefreshCw size={20} className={job?.state === "running" ? "spin" : ""} /> {job ? (job.state === "running" ? "Scanning…" : "Queued") : "Rescan"}
        </button>
        <button className="hbtn btn--danger" onClick={onRemove} data-testid={`library-remove-button-${lib.id}`}>
          <Trash2 size={20} /> Remove
        </button>
      </div>
    </article>
  );
}
