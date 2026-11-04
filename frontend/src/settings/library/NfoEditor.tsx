import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, post } from "../../api";
import { useAsync, useBack } from "../../hooks";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Choice, ResourceStatus } from "../ui";
import "./nfo.css";
import { useNfoLeaveGuard } from "./useNfoLeaveGuard";

type Kind = "movie" | "tv" | "episode";
type Item = { id: number; kind: Kind; title: string; year?: number | null; season_number?: number; episode_number?: number };
type Fields = { title: string; sort_title: string; year: number | null; plot: string; tagline: string; premiered: string; genres: string[];
  cast: { name: string; role: string }[]; rating: number | null; ids: Record<string,string>; set: string };
type Document = { id:number; kind:Kind; title:string; path:string; revision:string; document_key:string; fields:Fields|null; read_error?:string; backup_path?:string; warning?:string };

/** Read local sidecars supplied by other applications; save only the file explicitly opened by the host. */
export function NfoEditor() {
  const [params, setParams] = useSearchParams();
  const initialKind = params.get("nfo_kind");
  const initialId = Number(params.get("nfo_id"));
  const [selected, setSelected] = useState<Item | null>(() =>
    (initialKind === "movie" || initialKind === "tv" || initialKind === "episode") && Number.isInteger(initialId) && initialId > 0
      ? {kind:initialKind, id:initialId, title:""} : null);
  const [kind, setKind] = useState<"movie"|"tv">(initialKind === "tv" || initialKind === "episode" ? "tv" : "movie");
  const [show, setShow] = useState<Item | null>(null);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const activeKind = show ? "episode" : kind;
  const list = useAsync(() => api<{total:number;items:Item[]}>(`/api/nfo/items?kind=${activeKind}&query=${encodeURIComponent(search)}&offset=${offset}${show ? `&show_id=${show.id}` : ""}`), [activeKind, search, offset, show?.id]);
  const document = useAsync(() => selected ? api<Document>(`/api/nfo/document/${selected.kind}/${selected.id}`) : Promise.resolve(null), [selected?.kind,selected?.id]);
  const [fields, setFields] = useState<Fields | null>(null);
  const [genres, setGenres] = useState("");
  const [cast, setCast] = useState("");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [discard, setDiscard] = useState<"close"|"reload"|null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [operation, setOperation] = useState<"save"|"delete">("save");
  const [removed, setRemoved] = useState<string|null>(null);
  const inFlight = useRef(false);
  const opener = useRef<HTMLButtonElement | null>(null);
  const openerItem = useRef<Item | null>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const titleInput = useRef<HTMLInputElement>(null);
  const saveButton = useRef<HTMLButtonElement>(null);
  const deleteButton = useRef<HTMLButtonElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const opened = useRef("");
  const editorRoot = useRef<HTMLElement>(null);
  const locked = busy || document.loading;
  useNfoLeaveGuard(editorRoot,dirty,locked && !!selected,()=>setDirty(false));
  const data = document.data;
  useEffect(() => {
    if (!data) return;
    setFields(data.fields); setGenres(data.fields?.genres.join("\n")??""); setCast(data.fields?.cast.map(p=>`${p.name}${p.role ? ` | ${p.role}` : ""}`).join("\n")??""); setDirty(false);
    const key = `${data.kind}-${data.id}`;
    if (opened.current !== key) {
      opened.current = key;
      window.requestAnimationFrame(() => (titleInput.current??closeButton.current)?.focus());
    }
  }, [data]);
  const close = () => {
    setSelected(null); setFields(null); setError(null); setMessage(null); setDirty(false); opened.current="";
    const next = new URLSearchParams(params); next.delete("nfo_kind"); next.delete("nfo_id");
    if(next.toString()!==params.toString())setParams(next,{replace:true});
    window.requestAnimationFrame(() => {
      const item = openerItem.current;
      const restored = item ? window.document.querySelector<HTMLButtonElement>(`[data-testid="nfo-item-${item.kind}-${item.id}"] button`) : null;
      (restored ?? (opener.current?.isConnected ? opener.current : searchInput.current))?.focus();
    });
  };
  const reloadFile = async () => { setError(null); setMessage(null); await document.reload(); window.requestAnimationFrame(() => (titleInput.current ?? closeButton.current)?.focus()); };
  useBack(() => { if (busy) return true; if (dirty) setDiscard("close"); else close(); return true; },!!selected);
  const edit = <K extends keyof Fields>(key: K, value: Fields[K]) => { setFields(previous => previous ? {...previous,[key]:value} : previous); setDirty(true); setMessage(null); };
  const open = (item: Item, button: HTMLButtonElement) => { opener.current=button; openerItem.current=item; setSelected(item); setFields(null); setDirty(false); setError(null); setMessage(null); setRemoved(null); window.requestAnimationFrame(()=>closeButton.current?.focus()); };
  const save = async () => {
    if (inFlight.current || document.loading || !data || !selected || data.id!==selected.id || data.kind!==selected.kind || !fields || !dirty) return;
    inFlight.current=true; setBusy(true); setOperation("save"); setError(null); setMessage(null);
    const updated = {...fields, ids:Object.fromEntries(Object.entries(fields.ids).map(([key,value])=>[key,value.trim()]).filter(([,value])=>value)), genres:genres.split(/\n/).map(x=>x.trim()).filter(Boolean), cast:cast.split(/\n/).map(line=>{
      const split=line.indexOf("|"); return {name:(split<0?line:line.slice(0,split)).trim(),role:split<0?"":line.slice(split+1).trim()};
    }).filter(p=>p.name)};
    try {
      const saved=await post<Document>(`/api/nfo/document/${selected.kind}/${selected.id}`,{revision:data.revision,document_key:data.document_key,fields:updated});
      document.replaceData(saved); await list.reload();
      setMessage(saved.warning || `NFO saved. Backup: ${saved.backup_path}`);
    } catch(e) { setError(e instanceof Error?e.message:"Could not save the NFO file."); }
    finally { inFlight.current=false; setBusy(false); window.requestAnimationFrame(()=>saveButton.current?.focus()); }
  };
  const remove = async () => {
    setConfirmDelete(false);
    if(inFlight.current||document.loading||!data||!selected||data.id!==selected.id||data.kind!==selected.kind)return;
    inFlight.current=true;setBusy(true);setOperation("delete");setError(null);setMessage(null);
    try {
      const result=await post<{backup_path:string;message:string}>(`/api/nfo/document/${selected.kind}/${selected.id}/delete`,{revision:data.revision,document_key:data.document_key});
      close();setRemoved(`${result.message} Recovery backup: ${result.backup_path}`);await list.reload();
    } catch(e){setError(e instanceof Error?e.message:"Could not remove the NFO file.");}
    finally{inFlight.current=false;setBusy(false);window.requestAnimationFrame(()=>{if(selected&&deleteButton.current)deleteButton.current.focus();});}
  };
  return <section ref={editorRoot} className="lm-meta nfo-editor" data-testid="nfo-editor" aria-labelledby="nfo-editor-heading">
    <h3 id="nfo-editor-heading">Local NFO editor</h3>
    <p className="muted">REELHEIM reads metadata and artwork supplied by your other applications. Open an existing NFO to make corrections or remove an unwanted file. Saving and deletion keep a recovery backup. No online scraping or artwork downloads.</p>
    {removed&&<p className="form-ok nfo-path" role="status" data-testid="nfo-delete-result">{removed}</p>}
    {!selected && <>
      <Choice testId="nfo-kind" value={kind} onChange={value=>{setKind(value);setShow(null);setOffset(0);setSearch("");setQuery("");}} options={[{value:"movie",label:"Movies"},{value:"tv",label:"TV Shows"}]} />
      {show && <div className="nfo-actions"><strong>Episodes of {show.title}</strong><button className="hbtn" onClick={()=>{setShow(null);setOffset(0);setSearch("");setQuery("");window.requestAnimationFrame(()=>searchInput.current?.focus());}}>Back to TV shows</button></div>}
      <form className="nfo-search" onSubmit={e=>{e.preventDefault();setOffset(0);setSearch(query);}} data-nav-row>
        <label>Find a {show?"TV episode":kind==="movie"?"movie":"TV show"}<input ref={searchInput} value={query} maxLength={300} onChange={e=>setQuery(e.target.value)} data-testid="nfo-search-query" /></label>
        <button className="hbtn" type="submit" data-testid="nfo-search-button">Search library</button>
      </form>
      <ResourceStatus loading={list.loading} error={list.error} onRetry={list.reload} testId="nfo-list-load" label="local NFO titles" />
      {list.data?.total === 0 && <p data-testid="nfo-empty">No indexed titles in this selection. Add and scan a media source first.</p>}
      <div role="list" aria-label="Titles with local metadata" className="nfo-items">{list.data?.items.map(item=><div role="listitem" className="nfo-item" key={`${item.kind}-${item.id}`} data-testid={`nfo-item-${item.kind}-${item.id}`}>
        <strong>{item.kind==="episode"?`S${String(item.season_number).padStart(2,"0")}E${String(item.episode_number).padStart(2,"0")} · `:""}{item.title}{item.year?` (${item.year})`:""}</strong>
        <div className="nfo-actions" data-nav-row><button className="hbtn" onClick={e=>open(item,e.currentTarget)} aria-label={`Edit NFO for ${item.title}`}>Edit NFO</button>
          {item.kind==="tv" && <button className="hbtn" onClick={()=>{setShow(item);setOffset(0);setSearch("");setQuery("");window.requestAnimationFrame(()=>searchInput.current?.focus());}} aria-label={`Edit episodes of ${item.title}`}>Episodes</button>}</div>
      </div>)}</div>
      {list.data && list.data.total>20 && <div className="nfo-actions" data-nav-row>
        <button className="hbtn" disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-20))}>Previous</button><span>{offset+1}–{Math.min(offset+20,list.data.total)} of {list.data.total}</span>
        <button className="hbtn" disabled={offset+20>=list.data.total} onClick={()=>setOffset(offset+20)}>Next</button>
      </div>}
    </>}
    {selected && <div className="nfo-document" data-testid="nfo-document">
      <div className="nfo-actions"><button ref={closeButton} className="hbtn" disabled={busy} onClick={()=>dirty?setDiscard("close"):close()} data-testid="nfo-close">Close editor</button>
        <button className="hbtn" disabled={busy||document.loading} onClick={()=>dirty?setDiscard("reload"):reloadFile()} data-testid="nfo-reload">Reload from disk</button>
        {data&&<button ref={deleteButton} className="hbtn hbtn--danger" disabled={locked} onClick={()=>setConfirmDelete(true)} data-testid="nfo-delete">Delete NFO</button>}</div>
      <ResourceStatus loading={document.loading} error={document.error} onRetry={()=>dirty?setDiscard("reload"):reloadFile()} testId="nfo-document-load" label="NFO file" />
      {data&&<p className="nfo-path" data-testid="nfo-path">{data.path}</p>}
      {data?.read_error&&<p className="form-error" role="alert" data-testid="nfo-read-error">{data.read_error} You can repair it in your metadata application or use Delete NFO to remove it with a recovery backup.</p>}
      {data && fields && <form onSubmit={e=>{e.preventDefault();void save();}}>
        <p className="lm-fine">Only this NFO file is edited. Video files, artwork, episode ordering and watch progress stay in place. Tags outside these fields are preserved.</p>
        <div className="nfo-fields">
          <label>Title<input ref={titleInput} value={fields.title} maxLength={500} readOnly={locked} required onChange={e=>edit("title",e.target.value)} data-testid="nfo-title" /></label>
          <label>Sort title<input value={fields.sort_title} maxLength={500} readOnly={locked} onChange={e=>edit("sort_title",e.target.value)} data-testid="nfo-sort-title" /></label>
          <label>Year<input type="number" min={1800} max={2200} value={fields.year??""} readOnly={locked} onChange={e=>edit("year",e.target.value?Number(e.target.value):null)} data-testid="nfo-year" /></label>
          <label>Release / air date<input type="date" value={fields.premiered} readOnly={locked} onChange={e=>edit("premiered",e.target.value)} data-testid="nfo-date" /></label>
          <label className="nfo-wide">Tagline<input value={fields.tagline} maxLength={500} readOnly={locked} onChange={e=>edit("tagline",e.target.value)} data-testid="nfo-tagline" /></label>
          <label className="nfo-wide">Plot<textarea data-nav value={fields.plot} maxLength={50000} rows={6} readOnly={locked} onChange={e=>edit("plot",e.target.value)} data-testid="nfo-plot" /></label>
          <label>Genres (one per line)<textarea data-nav value={genres} rows={4} readOnly={locked} onChange={e=>{setGenres(e.target.value);setDirty(true);setMessage(null);}} data-testid="nfo-genres" /></label>
          <label>Cast (one per line: name | role)<textarea data-nav value={cast} rows={4} readOnly={locked} onChange={e=>{setCast(e.target.value);setDirty(true);setMessage(null);}} data-testid="nfo-cast" /></label>
          <label>Rating (0–10)<input type="number" min={0} max={10} step="any" value={fields.rating??""} readOnly={locked} onChange={e=>edit("rating",e.target.value?Number(e.target.value):null)} data-testid="nfo-rating" /></label>
          {selected.kind==="movie" && <label>Movie collection / set<input value={fields.set} maxLength={120} readOnly={locked} onChange={e=>edit("set",e.target.value)} data-testid="nfo-set" /></label>}
          {(["tmdb","tvdb","imdb"] as const).map(provider=><label key={provider}>{provider.toUpperCase()} ID<input value={fields.ids[provider]??""} maxLength={80} readOnly={locked} onChange={e=>edit("ids",{...fields.ids,[provider]:e.target.value})} data-testid={`nfo-id-${provider}`} /></label>)}
        </div>
        <p className="lm-fine">Provider IDs are local NFO identifiers only. No online lookup is performed.</p>
        <div className="nfo-actions" data-nav-row><button ref={saveButton} className="hbtn hbtn--primary" type="submit" aria-disabled={!dirty||locked||undefined} data-testid="nfo-save">{busy?(operation==="delete"?"Removing NFO…":"Saving NFO…"):"Save NFO & create backup"}</button><span>{dirty?"Unsaved changes":"No unsaved changes"}</span></div>
      </form>}
      {busy && <p role="status">{operation==="delete"?"Removing the NFO and keeping its recovery backup…":"Saving the NFO file and its backup…"}</p>}
      {error && <p className="form-error" role="alert" data-testid="nfo-save-error">{error} Your edits remain here. Reload from disk to use the latest version.</p>}
      {message && <p className="form-ok nfo-path" role="status" data-testid="nfo-save-result">{message}</p>}
    </div>}
    {discard && <ConfirmDialog title="Discard unsaved NFO changes?" message="Your changes have not been saved to the file. Discard them to continue." confirmLabel="Discard changes" onCancel={()=>setDiscard(null)} onConfirm={()=>{const next=discard;setDiscard(null);if(next==="reload")reloadFile();else close();}} />}
    {confirmDelete&&data&&<ConfirmDialog title="Delete this NFO?" message={`Remove ${data.path}? The original file will be kept beside it as a recovery .bak file. Any unsaved edits will be discarded. Media files, artwork and library titles are kept; rescan the source to refresh cached metadata.`} confirmLabel="Delete NFO & keep backup" onCancel={()=>setConfirmDelete(false)} onConfirm={()=>void remove()}/>}
  </section>;
}
