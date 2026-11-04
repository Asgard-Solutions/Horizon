import { ArrowUp, Check, Folder, HardDrive, House, Library, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useBack } from "../hooks";
import { focusFirst } from "../nav/spatial";

interface Root { name: string; path: string; type: string }
interface Listing { path: string; parent: string | null; dirs: { name: string; path: string }[]; video_files_here: number }

const ROOT_ICON: Record<string, typeof Folder> = { drive: HardDrive, home: House, library: Library, folder: Folder };

export function FolderBrowser({ onPick, onClose, initialPath }: { onPick: (path: string) => void; onClose: () => void; initialPath?: string }) {
  const [roots, setRoots] = useState<Root[]>([]);
  const [hint, setHint] = useState("");
  const [listing, setListing] = useState<Listing | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const modal = useRef<HTMLDivElement>(null);
  const sequence = useRef(0);
  const busy = useRef(false);
  const lastPath = useRef<string | null>(null);
  useBack(() => onClose());

  const open = async (path: string | null) => {
    if (busy.current) return;
    busy.current = true;
    const request = ++sequence.current;
    lastPath.current = path;
    setLoading(true); setError(null);
    try {
      if (path === null) {
        const r = await api<{ roots: Root[]; hint: string }>("/api/fs/roots");
        if (request !== sequence.current) return;
        setRoots(r.roots); setHint(r.hint); setListing(null);
      } else {
        const l = await api<Listing>(`/api/fs/list?path=${encodeURIComponent(path)}`);
        if (request !== sequence.current) return;
        setListing(l);
      }
    } catch (e) {
      if (request === sequence.current) setError((e as Error).message);
    } finally {
      if (request === sequence.current) {
        busy.current = false; setLoading(false);
        window.requestAnimationFrame(() => {
          if (modal.current && (document.activeElement === document.body || modal.current.contains(document.activeElement))) focusFirst(modal.current);
        });
      }
    }
  };
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    open(initialPath?.trim() || null);
    const focusFrame = window.requestAnimationFrame(() => focusFirst(modal.current));
    return () => {
      sequence.current++; busy.current = false;
      window.cancelAnimationFrame(focusFrame);
      if (opener?.isConnected && (document.activeElement === document.body || modal.current?.contains(document.activeElement))) opener.focus({ preventScroll: true });
    };
  }, []);

  return (
    <div className="modal-backdrop" data-nav-scope="modal" data-testid="folder-browser">
      <div ref={modal} className="modal" role="dialog" aria-label="Choose a media folder" aria-busy={loading}>
        <div className="modal-head">
          <h2>Choose a media folder</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Close" data-testid="folder-browser-close-button"><X size={28} /></button>
        </div>
        {loading && <p role="status" data-testid="folder-browser-loading">Loading folders…</p>}
        {error && <><p className="form-error" role="alert" data-testid="folder-browser-error">{error}</p>
          <button className="btn" onClick={() => open(lastPath.current)} data-testid="folder-browser-retry">Retry</button></>}
        {!listing ? (
          <>
            <div className="fb-list" data-testid="folder-browser-roots">
              {roots.map((r, i) => {
                const Icon = ROOT_ICON[r.type] ?? Folder;
                return (
                  <button key={r.path + r.type} className="fb-item" data-autofocus={i === 0 ? true : undefined}
                    aria-disabled={loading || undefined} onClick={() => open(r.path)} data-testid={`folder-root-${i}`}>
                    <Icon size={24} /><span>{r.name}</span><small>{r.path}</small>
                  </button>
                );
              })}
            </div>
            <p className="muted">{hint}</p>
          </>
        ) : (
          <>
            <div className="fb-current" data-testid="folder-browser-current-path">{listing.path}</div>
            <div className="fb-actions">
              <button className="btn btn--primary" data-autofocus aria-disabled={loading || undefined} onClick={() => { if (!busy.current) onPick(listing.path); }} data-testid="folder-browser-select-button">
                <Check size={22} /> Use this folder
              </button>
              <button className="btn" aria-disabled={loading || undefined} onClick={() => open(listing.parent)} data-testid="folder-browser-up-button">
                <ArrowUp size={22} /> {listing.parent ? "Up one level" : "All locations"}
              </button>
              <span className="muted" data-testid="folder-browser-video-count">{listing.video_files_here} video file(s) directly in this folder</span>
            </div>
            <div className="fb-list" data-testid="folder-browser-dirs">
              {listing.dirs.length === 0 && <p className="muted">No sub-folders.</p>}
              {listing.dirs.map((d) => (
                <button key={d.path} className="fb-item" aria-disabled={loading || undefined} onClick={() => open(d.path)} data-testid={`folder-dir-${d.name}`}>
                  <Folder size={24} /><span>{d.name}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
