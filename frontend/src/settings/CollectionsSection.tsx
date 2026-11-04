import { useState } from "react";
import { api, post } from "../api";
import { useAsync } from "../hooks";
import { SectionHead, SettingRow, Toggle } from "./ui";

/** Folder-based collections on/off. NFO <set> collections always apply; only the catalog is regrouped. */
export function CollectionsSection() {
  const { data, setData } = useAsync(() => api<{ folder_collections: boolean }>("/api/settings/library"), []);
  const [msg, setMsg] = useState<string | null>(null);
  if (!data) return null;
  const toggle = async (on: boolean) => {
    const r = await post<{ folder_collections: boolean; collections: number }>("/api/settings/library", { folder_collections: on });
    setData({ folder_collections: r.folder_collections });
    setMsg(`${r.collections} collection${r.collections === 1 ? "" : "s"} in your library now.`);
  };
  return (
    <div className="ssection" data-testid="settings-collections">
      <SectionHead title="Collections & folders" intro="Only Horizon's catalog is regrouped. Your folders and files are never changed." />
      <SettingRow label="NFO collections" testId="collections-nfo-row"
        hint={<>Collections named in NFO files (<code>&lt;set&gt;</code>) are always used.</>}>
        <span className="sbadge sbadge--on">Always on</span>
      </SettingRow>
      <SettingRow label="Folder groups" testId="collections-folder-row"
        hint="A folder that holds several movies becomes a collection. Generic folders such as Movies or Media never count.">
        <Toggle on={data.folder_collections} onChange={toggle} testId="folder-collections-toggle" />
      </SettingRow>
      {msg && <p className="form-hint" role="status" data-testid="folder-collections-result">{msg}</p>}
    </div>
  );
}
