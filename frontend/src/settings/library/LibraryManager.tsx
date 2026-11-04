import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, del, post } from "../../api";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { useAsync } from "../../hooks";
import type { Library, ScanStatus } from "../../types";
import { SectionHead } from "../ui";
import { AddSource } from "./AddSource";
import { MetadataReader } from "./MetadataReader";
import { ScanActivity } from "./ScanActivity";
import { SourceRow } from "./SourceRow";

const EMPTY: ScanStatus = { running: null, queued: [], recent: [] };

/** Libraries & scanning: sources, background scans (manual only), reachability and the metadata reader. */
export function LibraryManager() {
  const libs = useAsync(() => api<Library[]>("/api/libraries"), []);
  const [scans, setScans] = useState<ScanStatus>(EMPTY);
  const [confirming, setConfirming] = useState<Library | null>(null);
  const [error, setError] = useState<string | null>(null);
  const active = !!scans.running || scans.queued.length > 0;
  const wasActive = useRef(false);
  const lastReload = useRef(0);

  const poll = useCallback(() => api<ScanStatus>("/api/scans").then(setScans).catch(() => undefined), []);
  useEffect(() => { poll(); }, [poll]);
  useEffect(() => {
    const t = window.setInterval(poll, active ? 800 : 4000);
    return () => window.clearInterval(t);
  }, [active, poll]);
  // Refresh counts while scanning (titles appear as they are found) and once more when the queue drains.
  useEffect(() => {
    const now = Date.now();
    if ((active && now - lastReload.current > 3000) || (!active && wasActive.current)) {
      lastReload.current = now;
      libs.reload();
    }
    // The activity card (and its Cancel button) disappears when scans finish: keep controller focus on the page.
    if (!active && wasActive.current && (document.activeElement === document.body || !document.activeElement))
      document.querySelector<HTMLElement>('[data-testid="library-rescan-all-button"]')?.focus({ preventScroll: true });
    wasActive.current = active;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, scans.running?.files_found]);

  const scan = (library_id?: number) => post<ScanStatus>("/api/scans", { library_id }).then(setScans).catch((e: Error) => setError(e.message));
  const remove = async (lib: Library) => {
    setConfirming(null);
    await del(`/api/libraries/${lib.id}`).catch((e: Error) => setError(e.message));
    libs.reload();
    poll();
  };
  const jobFor = (id: number) => (scans.running?.library_id === id ? scans.running : scans.queued.find((q) => q.library_id === id));

  return (
    <div className="ssection" data-testid="settings-libraries">
      <SectionHead title="Libraries & scanning"
        intro="Horizon reads your folders and never moves, renames, changes or deletes media files. Scans run only when you ask, in the background." />
      <div className="lm-toolbar" data-nav-row>
        <button className="hbtn hbtn--primary" onClick={() => scan()} disabled={!libs.data?.length} data-testid="library-rescan-all-button">
          <RefreshCw size={22} /> Rescan all
        </button>
        <span className="lm-fine" data-testid="library-summary">
          {libs.data ? `${libs.data.length} source${libs.data.length === 1 ? "" : "s"} · ${libs.data.filter((l) => !l.reachable).length} not reachable` : ""}
        </span>
      </div>
      <ScanActivity status={scans} onChange={setScans} />
      {error && <p className="form-error" role="alert" data-testid="library-error">{error}</p>}
      {libs.error && <p className="form-error">{libs.error}</p>}
      <div className="lm-list" data-testid="library-list">
        {libs.data?.length === 0 && <p className="lm-empty" data-testid="library-list-empty">No media sources yet. Add a folder on this PC or a network share below.</p>}
        {libs.data?.map((lib) => (
          <SourceRow key={lib.id} lib={lib} job={jobFor(lib.id)} onRescan={() => scan(lib.id)} onRemove={() => setConfirming(lib)} />
        ))}
      </div>
      <h3 className="ssub">Add a source</h3>
      <AddSource onAdded={() => { libs.reload(); poll(); }} />
      <h3 className="ssub">Background reading</h3>
      <MetadataReader />
      {confirming && (
        <ConfirmDialog title={`Remove "${confirming.name}"?`} confirmLabel="Remove from library"
          message="Only Horizon's catalog entries are removed. Your files on disk are not touched. Watch progress is kept and returns if you add this folder again."
          onConfirm={() => remove(confirming)} onCancel={() => setConfirming(null)} />
      )}
    </div>
  );
}
