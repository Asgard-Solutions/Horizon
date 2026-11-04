import { FolderOpen, FolderPlus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { post } from "../../api";
import { FolderBrowser } from "../../components/FolderBrowser";
import type { Library } from "../../types";

/** Adds a local or network folder, then queues its first scan in the background. */
export function AddSource({ onAdded }: { onAdded: (lib: Library) => void }) {
  const [params] = useSearchParams();
  const requestedPath = params.get("source_path");
  const [path, setPath] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [browsing, setBrowsing] = useState(false);
  const adding = useRef(false);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => { if (requestedPath && !adding.current) setPath(requestedPath); }, [requestedPath]);
  const networkParams = new URLSearchParams(params);
  networkParams.set("section", "network"); networkParams.delete("source_path");

  const add = async (p = path) => {
    if (adding.current || !p.trim()) return;
    adding.current = true;
    setError(null);
    setBusy(true);
    try {
      const lib = await post<Library>("/api/libraries", { path: p, scan: false });
      setPath("");
      onAdded(lib);
      try { await post("/api/scans", { library_id: lib.id }); onAdded(lib); }
      catch (e) { setError(`Source added, but its scan could not start. Use Rescan to try again. ${(e as Error).message}`); }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      adding.current = false;
      setBusy(false);
      window.requestAnimationFrame(() => {
        if (input.current?.isConnected && document.activeElement === document.body) input.current.focus();
      });
    }
  };

  return (
    <div className="lm-add" data-testid="library-add-source">
      <form className="add-folder" data-nav-row onSubmit={(e) => { e.preventDefault(); add(); }}>
        <input ref={input} value={path} readOnly={busy} onChange={(e) => { setPath(e.target.value); setError(null); }} placeholder={String.raw`D:\Movies  or  \\NAS\Media`}
          aria-label="Folder path" data-testid="library-path-input" />
        <button type="button" className="hbtn" aria-disabled={busy || undefined} onClick={() => { if (!busy) setBrowsing(true); }} data-testid="library-browse-button">
          <FolderOpen size={22} /> Browse
        </button>
        <button type="submit" className="hbtn hbtn--primary" disabled={!path.trim() && !busy} aria-disabled={busy || undefined} data-testid="library-add-button">
          <FolderPlus size={22} /> {busy ? "Adding…" : "Add source"}
        </button>
      </form>
      <p className="lm-fine">Network shares: use the full path (<code>\\NAS\Share</code>). Mapped drive letters are not visible to every Windows account.</p>
      <p className="lm-fine">Need to sign in to a NAS? <Link to={`/settings?${networkParams}`}>Set up a network connection</Link>, then return here to add its media folder.</p>
      {error && <p className="form-error" role="alert" data-testid="library-form-error">{error}</p>}
      {browsing && <FolderBrowser initialPath={path} onClose={() => setBrowsing(false)} onPick={(p) => { setBrowsing(false); setPath(p); add(p); }} />}
    </div>
  );
}
