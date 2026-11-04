import { Loader2, X } from "lucide-react";
import { post } from "../../api";
import { useRef, useState } from "react";
import type { ScanStatus } from "../../types";

/** Live background-scan card: active source, files found so far, current folder, queue, and Cancel. */
export function ScanActivity({ status, onChange }: { status: ScanStatus; onChange: (s: ScanStatus) => void }) {
  const inFlight = useRef(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const job = status.running;
  if (!job && !status.queued.length) return null;
  const cancel = async (job_id?: string) => {
    if (inFlight.current) return;
    inFlight.current = true; setPending(true); setError(null);
    try { onChange(await post<ScanStatus>("/api/scans/cancel", { job_id })); }
    catch (e) { setError((e as Error).message); }
    finally { inFlight.current = false; setPending(false); }
  };
  return (
    <section className="lm-activity" role="status" aria-live="polite" data-testid="scan-activity">
      <Loader2 size={30} className="spin lm-activity-icon" aria-hidden="true" />
      <div className="lm-activity-text">
        <span className="lm-eyebrow">Scanning in the background · you can keep browsing</span>
        {job && (
          <>
            <strong data-testid="scan-activity-source">{job.library_name}</strong>
            <span data-testid="scan-activity-files">{job.files_found.toLocaleString()} video files found so far</span>
            <code className="lm-current" data-testid="scan-activity-current">{job.current ? `…/${job.current}` : job.path}</code>
          </>
        )}
        {status.queued.length > 0 && (
          <span className="lm-queue" data-testid="scan-activity-queue">Next: {status.queued.map((q) => q.library_name).join(", ")}</span>
        )}
        <span className="lm-bar" aria-hidden="true"><span /></span>
        {pending && <span role="status">Cancelling scan…</span>}
        {error && <p className="form-error" role="alert" data-testid="scan-cancel-error">Could not cancel scan: {error}</p>}
      </div>
      <div className="lm-activity-actions" data-nav-row>
        {job && <button className="hbtn" aria-disabled={pending || undefined} onClick={() => cancel(job.id)} data-testid="scan-cancel-button"><X size={22} /> Cancel scan</button>}
        {(status.queued.length > 0) && <button className="hbtn hbtn--quiet" aria-disabled={pending || undefined} onClick={() => cancel()} data-testid="scan-cancel-all-button">Cancel all</button>}
      </div>
    </section>
  );
}
