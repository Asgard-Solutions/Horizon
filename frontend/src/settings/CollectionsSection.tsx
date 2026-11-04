import { useRef, useState } from "react";
import { api, post } from "../api";
import { useAsync } from "../hooks";
import { ResourceStatus, SectionHead, SettingRow, Toggle } from "./ui";

type CollectionPrefs = { nfo_collections: boolean; folder_collections: boolean };

/** Independent NFO and folder collections; only the indexed catalog is regrouped. */
export function CollectionsSection() {
  const { data, replaceData: setData, loading, error, reload } = useAsync(() => api<CollectionPrefs>("/api/settings/library"), []);
  const savingRef = useRef(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const toggle = async (key: keyof CollectionPrefs, on: boolean) => {
    if (savingRef.current || !data) return;
    savingRef.current = true;
    setSaving(true);
    setSaveError(null);
    setMsg(null);
    try {
      const r = await post<CollectionPrefs & { collections: number }>("/api/settings/library", { [key]: on });
      setData({ nfo_collections: r.nfo_collections, folder_collections: r.folder_collections });
      setMsg(`${r.collections} collection${r.collections === 1 ? "" : "s"} in your library now.`);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Could not save collection settings.");
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };
  return (
    <div className="ssection" data-testid="settings-collections">
      <SectionHead title="Collections & folders" intro="Only REELHEIM's catalog is regrouped. Your folders and files are never changed." />
      <ResourceStatus loading={loading} error={error} onRetry={reload} testId="collections-load" />
      {data && <>
        <SettingRow label="NFO collections" testId="collections-nfo-row"
          hint={<>Use collections named in NFO files (<code>&lt;set&gt;</code>). When on, these take priority over folder groups.</>}>
          <Toggle on={data.nfo_collections} onChange={(on) => toggle("nfo_collections", on)} disabled={saving} testId="nfo-collections-toggle" />
        </SettingRow>
        <SettingRow label="Folder groups" testId="collections-folder-row"
          hint="A folder that holds several movies becomes a collection. Generic folders such as Movies or Media never count.">
          <Toggle on={data.folder_collections} onChange={(on) => toggle("folder_collections", on)} disabled={saving} testId="folder-collections-toggle" />
        </SettingRow>
        {(saving || msg) && <p className="form-hint" role="status" data-testid="folder-collections-result">{saving ? "Updating collections…" : msg}</p>}
        {saveError && <p className="form-error" role="alert" data-testid="collections-save-error">{saveError}</p>}
      </>}
    </div>
  );
}
