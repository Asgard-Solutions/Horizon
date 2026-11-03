import { ArrowUp, Check, Folder, HardDrive, House, Library, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { useBack } from "../hooks";
import { focusFirst } from "../nav/spatial";

interface Root { name: string; path: string; type: string }
interface Listing { path: string; parent: string | null; dirs: { name: string; path: string }[]; video_files_here: number }

const ROOT_ICON: Record<string, typeof Folder> = { drive: HardDrive, home: House, library: Library, folder: Folder };

export function FolderBrowser({ onPick, onClose }: { onPick: (path: string) => void; onClose: () => void }) {
  const [roots, setRoots] = useState<Root[]>([]);
  const [hint, setHint] = useState("");
  const [listing, setListing] = useState<Listing | null>(null);
  const [error, setError] = useState<string | null>(null);
  useBack(() => onClose());

  useEffect(() => {
    api<{ roots: Root[]; hint: string }>("/api/fs/roots").then((r) => { setRoots(r.roots); setHint(r.hint); })
      .catch((e: Error) => setError(e.message));
  }, []);

  const open = (path: string) => {
    setError(null);
    api<Listing>(`/api/fs/list?path=${encodeURIComponent(path)}`)
      .then((l) => { setListing(l); window.setTimeout(() => focusFirst(document.querySelector(".modal")), 30); })
      .catch((e: Error) => setError(e.message));
  };

  return (
    <div className="modal-backdrop" data-nav-scope="modal" data-testid="folder-browser">
      <div className="modal" role="dialog" aria-label="Choose a media folder">
        <div className="modal-head">
          <h2>Choose a folder on this PC</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Close" data-testid="folder-browser-close-button"><X size={28} /></button>
        </div>
        {error && <p className="form-error" role="alert" data-testid="folder-browser-error">{error}</p>}
        {!listing ? (
          <>
            <div className="fb-list" data-testid="folder-browser-roots">
              {roots.map((r, i) => {
                const Icon = ROOT_ICON[r.type] ?? Folder;
                return (
                  <button key={r.path + r.type} className="fb-item" data-autofocus={i === 0 ? true : undefined}
                    onClick={() => open(r.path)} data-testid={`folder-root-${i}`}>
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
              <button className="btn btn--primary" data-autofocus onClick={() => onPick(listing.path)} data-testid="folder-browser-select-button">
                <Check size={22} /> Use this folder
              </button>
              <button className="btn" onClick={() => (listing.parent ? open(listing.parent) : setListing(null))} data-testid="folder-browser-up-button">
                <ArrowUp size={22} /> {listing.parent ? "Up one level" : "All locations"}
              </button>
              <span className="muted" data-testid="folder-browser-video-count">{listing.video_files_here} video file(s) directly in this folder</span>
            </div>
            <div className="fb-list" data-testid="folder-browser-dirs">
              {listing.dirs.length === 0 && <p className="muted">No sub-folders.</p>}
              {listing.dirs.map((d) => (
                <button key={d.path} className="fb-item" onClick={() => open(d.path)} data-testid={`folder-dir-${d.name}`}>
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
