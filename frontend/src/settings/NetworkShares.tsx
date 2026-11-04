import { FolderOpen, Network } from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { post } from "../api";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { Choice, Toggle } from "./ui";
import type { NetworkInfo, NetworkLocation } from "./networkTypes";
import "./network.css";

type Account = "windows" | "custom" | "saved";

/** Establish a host Windows SMB session; actual source addition stays in Libraries & scanning. */
export function NetworkShares({ info, reload }: { info: NetworkInfo; reload: () => Promise<void> }) {
  const [server, setServer] = useState("");
  const [share, setShare] = useState("");
  const [folder, setFolder] = useState("");
  const [account, setAccount] = useState<Account>("windows");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [result, setResult] = useState<NetworkLocation | null>(null);
  const [forgetting, setForgetting] = useState<NetworkLocation | null>(null);
  const active = useRef(false);
  const serverInput = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const supported = info.capabilities.smb_supported;
  const operation = async (action: () => Promise<void>) => {
    if (active.current) return;
    active.current = true; setBusy(true); setError(null); setMessage(null);
    try { await action(); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not complete the share connection."); }
    finally {
      active.current = false; setBusy(false);
      window.requestAnimationFrame(() => { if (document.activeElement === document.body) serverInput.current?.focus({ preventScroll: false }); });
    }
  };
  const connect = () => operation(async () => {
    const body = { server, share, folder, account, ...(account === "custom" ? { username, password, remember } : {}) };
    setPassword(""); setResult(null);
    const connected = await post<NetworkLocation>("/api/network/shares/connect", body);
    setResult(connected);
    setMessage(connected.credential_saved ? "Connected and folder access checked. Sign-in is saved securely on this PC." : "Connected and folder access checked. No new sign-in was saved.");
    await reload();
  });
  const edit = (change: () => void) => { change(); setResult(null); setError(null); setMessage(null); };
  const startNew = () => {
    if (active.current) return;
    setServer(""); setShare(""); setFolder(""); setAccount("windows");
    setUsername(""); setPassword(""); setRemember(false);
    setResult(null); setError(null); setMessage(null);
    serverInput.current?.focus({ preventScroll: false });
  };
  const openLibrary = (location: NetworkLocation) => {
    const next = new URLSearchParams(params);
    next.set("section", "libraries"); next.set("source_path", location.path);
    navigate(`/settings?${next}`);
  };
  const useLocation = (location: NetworkLocation) => {
    setServer(location.server); setShare(location.share); setFolder(location.folder ?? "");
    setAccount(location.credential_saved ? "saved" : "windows"); setPassword(""); setRemember(false);
    setResult(null); setError(null); setMessage(null);
    serverInput.current?.focus({ preventScroll: false });
  };
  return <section className="network-shares" data-testid="network-shares">
    <div className="network-share-heading">
      <h3><Network size={24} aria-hidden="true" /> Connect to a NAS or shared folder</h3>
      <button className="hbtn" type="button" aria-disabled={busy || undefined} onClick={startNew} disabled={!supported} data-testid="smb-add-another">
        {info.connections.length ? "Add another location" : "New location"}
      </button>
    </div>
    <p className="muted">Add multiple NAS servers, shares or folders on your home network. Each successful connection appears below; adding another keeps existing locations. Connection setup does not scan or change files.</p>
    {!supported && <p className="notice" data-testid="smb-unsupported">SMB sign-in setup requires the Windows host. On another operating system, mount the share there and add its local folder under Libraries & scanning.</p>}
    <form className="network-share-form" aria-busy={busy} onSubmit={e => { e.preventDefault(); if (supported) void connect(); }}>
      <div className="network-share-fields" data-nav-row>
        <label>Server name or IP<input ref={serverInput} value={server} readOnly={busy} disabled={!supported} maxLength={253}
          onChange={e => edit(() => setServer(e.target.value))} placeholder="NAS or 192.168.1.50" autoComplete="off" spellCheck={false} data-testid="smb-server" /></label>
        <label>Shared folder<input value={share} readOnly={busy} disabled={!supported} maxLength={80}
          onChange={e => edit(() => setShare(e.target.value))} placeholder="Media" autoComplete="off" spellCheck={false} data-testid="smb-share" /></label>
        <label>Subfolder (optional)<input value={folder} readOnly={busy} disabled={!supported} maxLength={1024}
          onChange={e => edit(() => setFolder(e.target.value))} placeholder="Movies" autoComplete="off" spellCheck={false} data-testid="smb-folder" /></label>
      </div>
      <div className="network-account-choice"><strong>Sign in using</strong>
        <Choice<Account> value={account} testId="smb-account" disabled={!supported} busy={busy}
          onChange={value => edit(() => { setAccount(value); setPassword(""); setRemember(false); })}
          options={[{ value: "windows", label: "Windows sign-in" }, { value: "custom", label: "Another account" }, { value: "saved", label: "Saved sign-in" }]} />
      </div>
      {account === "windows" && <p className="lm-fine">Uses the Windows account running REELHEIM and any connection it already has. No new password is stored.</p>}
      {account === "saved" && <p className="lm-fine">Uses a sign-in previously saved by REELHEIM for this server and share.</p>}
      {account === "custom" && <>
        <div className="network-share-fields" data-nav-row>
          <label>Username<input value={username} readOnly={busy} maxLength={256} onChange={e => edit(() => setUsername(e.target.value))}
            placeholder="NAS\username or username" autoComplete="off" spellCheck={false} data-testid="smb-username" /></label>
          <label>Password<input type="password" value={password} readOnly={busy} maxLength={512} onChange={e => edit(() => setPassword(e.target.value))}
            autoComplete="new-password" data-testid="smb-password" /></label>
        </div>
        <div className="network-remember"><span>Remember this sign-in on this PC</span>
          <Toggle on={remember} disabled={busy || !info.capabilities.credential_store_supported} onChange={setRemember} testId="smb-remember" />
        </div>
        <p className="lm-fine">Remember uses Windows Credential Manager for the Windows account running REELHEIM. Passwords are not saved in REELHEIM's database. The password field clears after each attempt.</p>
      </>}
      <button className="hbtn hbtn--primary" type="submit" disabled={!supported || !server.trim() || !share.trim() || (account === "custom" && !username.trim())}
        aria-disabled={busy || undefined} data-testid="smb-connect">{busy ? "Connecting…" : "Connect & test folder"}</button>
    </form>
    {busy && <p role="status" data-testid="smb-pending">Checking the server, sign-in and folder access…</p>}
    {error && <p className="form-error" role="alert" data-testid="smb-error">{error}</p>}
    {message && <p className="form-ok" role="status" data-testid="smb-result">{message}</p>}
    {result && <div className="network-share-result" data-testid="smb-connected-folder">
      <code>{result.path}</code>
      <button className="hbtn" onClick={() => openLibrary(result)}><FolderOpen size={22} aria-hidden="true" /> Open in Libraries & scanning</button>
      <p className="lm-fine">Browse to the media folder there, then choose Add source. Existing sources are managed in that same place.</p>
    </div>}
    {info.connections.length > 0 && <>
      <h3 data-testid="smb-location-count">Network locations ({info.connections.length})</h3><p className="lm-fine">These saved locations are not a live availability check. Library sources are managed in Libraries & scanning. Locations on the same share use the same saved sign-in.</p>
      <div className="network-location-list" role="list" aria-label="Network locations">{info.connections.map(location => <div className="network-location" role="listitem" key={location.id} data-testid={`smb-location-${location.id}`}>
        <div><strong>{location.server} / {location.share}{location.folder ? ` / ${location.folder}` : ""}</strong><code>{location.path}</code><span className="lm-fine">{location.credential_saved ? "Sign-in saved on this PC" : "Sign-in not saved"}</span></div>
        <button className="hbtn" aria-label={`Set up connection to ${location.path}`} aria-disabled={busy || undefined} onClick={() => { if (!busy) useLocation(location); }}>Set up connection</button>
        <button className="hbtn" aria-label={`Open ${location.path} in Libraries`} aria-disabled={busy || undefined} onClick={() => { if (!busy) openLibrary(location); }}>Open in Libraries</button>
        {location.credential_saved && <button className="hbtn btn--danger" aria-label={`Forget saved sign-in for ${location.share_path}`} aria-disabled={busy || undefined} onClick={() => { if (!busy) setForgetting(location); }}>Forget saved sign-in</button>}
      </div>)}</div>
    </>}
    {forgetting && <ConfirmDialog title="Forget saved share sign-in?" message={`Forget the sign-in saved for ${forgetting.server} / ${forgetting.share}? This affects the saved sign-in for every location on that share. Existing Windows connections and library sources will stay in place.`}
      confirmLabel="Forget sign-in" onCancel={() => setForgetting(null)} onConfirm={() => {
        const location = forgetting; setForgetting(null);
        void operation(async () => { await post("/api/network/shares/forget", { server: location.server, share: location.share }); setMessage("Saved sign-in forgotten. Existing connections and sources are unchanged."); await reload(); });
      }} />}
  </section>;
}
