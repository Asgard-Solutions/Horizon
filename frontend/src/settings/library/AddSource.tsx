import { FolderOpen, FolderPlus } from "lucide-react";
import { useState } from "react";
import { post } from "../../api";
import { FolderBrowser } from "../../components/FolderBrowser";
import type { Library } from "../../types";

/** Adds a local or network folder, then queues its first scan in the background. */
export function AddSource({ onAdded }: { onAdded: (lib: Library) => void }) {
  const [path, setPath] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [browsing, setBrowsing] = useState(false);

  const add = async (p = path) => {
    setError(null);
    setBusy(true);
    try {
      const lib = await post<Library>("/api/libraries", { path: p, scan: false });
      await post("/api/scans", { library_id: lib.id });
      setPath("");
      onAdded(lib);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="lm-add" data-testid="library-add-source">
      <form className="add-folder" onSubmit={(e) => { e.preventDefault(); add(); }}>
        <input value={path} onChange={(e) => { setPath(e.target.value); setError(null); }} placeholder={String.raw`D:\Movies  or  \\NAS\Media`}
          aria-label="Folder path" data-testid="library-path-input" />
        <button type="button" className="hbtn" onClick={() => setBrowsing(true)} data-testid="library-browse-button">
          <FolderOpen size={22} /> Browse
        </button>
        <button type="submit" className="hbtn hbtn--primary" disabled={!path.trim() || busy} data-testid="library-add-button">
          <FolderPlus size={22} /> {busy ? "Adding…" : "Add source"}
        </button>
      </form>
      <p className="lm-fine">Network shares: use the full path (<code>\\NAS\Share</code>). Mapped drive letters are not visible to every Windows account.</p>
      {error && <p className="form-error" role="alert" data-testid="library-form-error">{error}</p>}
      {browsing && <FolderBrowser onClose={() => setBrowsing(false)} onPick={(p) => { setBrowsing(false); setPath(p); add(p); }} />}
    </div>
  );
}
