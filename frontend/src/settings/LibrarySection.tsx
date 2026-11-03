import { FolderOpen, FolderPlus, RefreshCw, Trash2 } from "lucide-react";
import { useState } from "react";
import { api, del, post } from "../api";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { FolderBrowser } from "../components/FolderBrowser";
import { useAsync } from "../hooks";
import type { Library, ScanSummary } from "../types";

function Summary({ s, testId }: { s: ScanSummary; testId: string }) {
  return (
    <div className="scan-summary" data-testid={testId}>
      <span>{s.files_found} videos found</span>
      <span>{s.movies} movies</span>
      <span>{s.episodes} episodes</span>
      <span>{s.added} new</span>
      <span>{s.updated} changed</span>
      <span>{s.removed} removed</span>
      {s.errors.map((e) => <span key={e} className="form-error">{e}</span>)}
    </div>
  );
}

export function LibrarySection() {
  const { data, error, loading, reload } = useAsync(() => api<Library[]>("/api/libraries"), []);
  const [path, setPath] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [browsing, setBrowsing] = useState(false);
  const [lastScan, setLastScan] = useState<{ id: number; summary: ScanSummary } | null>(null);
  const [confirming, setConfirming] = useState<Library | null>(null);

  const add = async (p = path) => {
    setFormError(null);
    setBusy("add");
    try {
      const lib = await post<Library>("/api/libraries", { path: p, scan: true });
      setPath("");
      if (lib.scan) setLastScan({ id: lib.id, summary: lib.scan });
      await reload();
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };
  const rescan = async (id: number) => {
    setBusy(`scan-${id}`);
    setFormError(null);
    try {
      const lib = await post<Library>(`/api/libraries/${id}/scan`);
      if (lib.scan) setLastScan({ id, summary: lib.scan });
      await reload();
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };
  const remove = async (lib: Library) => {
    setConfirming(null);
    setFormError(null);
    await del(`/api/libraries/${lib.id}`).catch((e: Error) => setFormError(e.message));
    reload();
  };

  return (
    <section className="panel" data-testid="settings-libraries">
      <h2>Library folders</h2>
      <p className="muted">Folders are scanned recursively for MP4, MKV, AVI, M4V and other video files. Media files are only read — never moved, renamed, changed or deleted.</p>
      <form className="add-folder" onSubmit={(e) => { e.preventDefault(); add(); }}>
        <input value={path} onChange={(e) => setPath(e.target.value)} placeholder={String.raw`D:\Movies  or  \\NAS\Media`}
          aria-label="Folder path" data-testid="library-path-input" />
        <button type="button" className="btn" onClick={() => setBrowsing(true)} data-testid="library-browse-button">
          <FolderOpen size={22} /> Browse
        </button>
        <button type="submit" className="btn btn--primary" disabled={!path.trim() || busy === "add"} data-testid="library-add-button">
          <FolderPlus size={22} /> {busy === "add" ? "Adding & scanning…" : "Add & scan"}
        </button>
      </form>
      {formError && <p className="form-error" role="alert" data-testid="library-form-error">{formError}</p>}
      {error && <p className="form-error">{error}</p>}
      <div className="lib-list" data-testid="library-list">
        {loading && !data && <p className="muted" data-testid="library-list-loading">Loading folders…</p>}
        {data?.length === 0 && <p className="muted" data-testid="library-list-empty">No folders added yet.</p>}
        {data?.map((lib) => (
          <div key={lib.id} className="lib-item" data-testid={`library-item-${lib.id}`}>
            <div className="lib-text">
              <strong>{lib.name}</strong>
              <code data-testid={`library-path-${lib.id}`}>{lib.path}</code>
              <span className="muted" data-testid={`library-counts-${lib.id}`}>
                {lib.counts.movies} movies · {lib.counts.episodes} episodes
                {lib.last_scan_at ? ` · scanned ${new Date(lib.last_scan_at).toLocaleString()}` : ""}
                {!lib.reachable && " · NOT REACHABLE"}
              </span>
              {lastScan?.id === lib.id && <Summary s={lastScan.summary} testId={`library-scan-summary-${lib.id}`} />}
            </div>
            <button className="btn" onClick={() => rescan(lib.id)} disabled={busy === `scan-${lib.id}`} data-testid={`library-rescan-button-${lib.id}`}>
              <RefreshCw size={20} className={busy === `scan-${lib.id}` ? "spin" : ""} /> Rescan
            </button>
            <button className="btn btn--danger" onClick={() => setConfirming(lib)} data-testid={`library-remove-button-${lib.id}`}>
              <Trash2 size={20} /> Remove
            </button>
          </div>
        ))}
      </div>
      {confirming && (
        <ConfirmDialog title={`Remove "${confirming.name}"?`} confirmLabel="Remove from library"
          message="Only the catalog entries are removed. Your files on disk are not touched. Watch progress is kept."
          onConfirm={() => remove(confirming)} onCancel={() => setConfirming(null)} />
      )}
      {browsing && (
        <FolderBrowser onClose={() => setBrowsing(false)} onPick={(p) => { setBrowsing(false); setPath(p); add(p); }} />
      )}
    </section>
  );
}
