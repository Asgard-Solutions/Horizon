import { useState } from "react";
import { api, post } from "../api";
import { useAsync } from "../hooks";

/** Folder-based collections on/off. NFO <set> collections always apply; only the catalog is regrouped. */
export function CollectionsSection() {
  const { data, setData } = useAsync(() => api<{ folder_collections: boolean }>("/api/settings/library"), []);
  const [msg, setMsg] = useState<string | null>(null);
  if (!data) return null;
  const toggle = async () => {
    const r = await post<{ folder_collections: boolean; collections: number }>("/api/settings/library", { folder_collections: !data.folder_collections });
    setData({ folder_collections: r.folder_collections });
    setMsg(`${r.collections} collection${r.collections === 1 ? "" : "s"} in your library now.`);
  };
  return (
    <section className="panel" data-testid="settings-collections">
      <h2>Collections</h2>
      <p>Collections named in NFO files (<code>&lt;set&gt;</code>) are always used. Folder groups treat a folder that holds several movies
        as a collection (generic folders such as Movies or Media never count). Your files are not changed.</p>
      <button className={`btn${data.folder_collections ? " btn--primary" : ""}`} role="switch" aria-checked={data.folder_collections}
        onClick={toggle} data-testid="folder-collections-toggle">
        Folder groups: {data.folder_collections ? "On" : "Off"}
      </button>
      {msg && <p className="form-hint" data-testid="folder-collections-result">{msg}</p>}
    </section>
  );
}
