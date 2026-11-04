import { KeyRound, ShieldCheck, ShieldOff, Wifi, WifiOff } from "lucide-react";
import { useRef, useState } from "react";
import { api, del, post } from "../api";
import { useAsync } from "../hooks";
import type { Device, SystemInfo } from "../types";
import { ResourceStatus } from "./ui";
import { focusables } from "../nav/spatial";
import { NetworkShares } from "./NetworkShares";
import type { NetworkInfo } from "./networkTypes";

export function NetworkSection({ system, onChange, onReload }: { system: SystemInfo; onChange: (s: SystemInfo) => void; onReload: () => Promise<void> }) {
  const devices = useAsync(() => api<Device[]>("/api/devices"), []);
  const network = useAsync(() => api<NetworkInfo>("/api/network"), []);
  const [pin, setPin] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [pending, setPending] = useState(false);
  const inFlight = useRef(false);
  const section = useRef<HTMLElement>(null);
  const lan = system.lan;

  const perform = async (operation: () => Promise<void>) => {
    if (inFlight.current) return;
    inFlight.current = true;
    const initiator = document.activeElement as HTMLElement | null;
    setPending(true);
    setMsg(null);
    try {
      await operation();
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    } finally {
      inFlight.current = false;
      setPending(false);
      window.requestAnimationFrame(() => {
        if (document.activeElement === document.body || (document.activeElement === initiator && initiator?.matches(":disabled")))
          focusables().find((element) => section.current?.contains(element))?.focus({ preventScroll: true });
      });
    }
  };
  const savePin = () => {
    if (pin.length < 8) return;
    return perform(async () => {
      const r = await post<{ revoked_devices: number }>("/api/settings/pin", { pin, revoke_devices: true });
      setPin("");
      setMsg({ ok: true, text: `PIN saved.${r.revoked_devices ? ` ${r.revoked_devices} paired device(s) must pair again.` : ""}` });
      await Promise.all([onReload(), devices.reload()]);
    });
  };
  const toggleLan = () => perform(async () => {
      onChange(await post<SystemInfo>("/api/settings/lan", { enabled: !lan.enabled }));
      setMsg({ ok: true, text: "Network setting saved." });
  });
  const revoke = (id: number) => perform(async () => {
    await del(`/api/devices/${id}`);
    await devices.reload();
    setMsg({ ok: true, text: "Device access revoked." });
  });

  return (
    <section ref={section} className="panel" data-testid="settings-network">
      <h2>Network & devices</h2>
      <p className="muted">Connect this PC to NAS folders below, or let paired devices on your home network open REELHEIM. Wi-Fi, Ethernet and firewall settings are managed by Windows.</p>
      <h3>Devices opening REELHEIM</h3>
      <p className="muted">Other devices use this host's address and access PIN. They do not need the NAS password. Public internet clients are refused.</p>
      <div className="lan-status" data-testid="lan-status">
        {lan.enabled ? <Wifi size={28} className="ok" /> : <WifiOff size={28} />}
        <strong data-testid="lan-status-text">Device access is {lan.enabled ? "enabled" : "disabled"}</strong>
        <button className={lan.enabled ? "btn btn--danger" : "btn btn--primary"} onClick={toggleLan} disabled={!lan.pin_configured && !lan.enabled} aria-disabled={pending || undefined}
          data-testid="lan-toggle-button">
          {lan.enabled ? "Turn off LAN access" : "Turn on LAN access"}
        </button>
      </div>
      {lan.restart_required && (
        <p className="notice" data-testid="lan-restart-notice">Restart the server (close the window and run start.bat again) to apply this change.</p>
      )}
      {lan.bind_host === null && (
        <p className="muted" data-testid="lan-bind-unmanaged">Server was started directly by uvicorn, so its network binding is managed outside the app.</p>
      )}
      <ResourceStatus loading={network.loading && !network.data} error={network.error} onRetry={network.reload} testId="network-connections-load" label="connections" />
      {network.data && <div className="network-listener" data-testid="network-listener">
        <dl className="sfacts"><dt>Host PC</dt><dd>{network.data.hostname}</dd><dt>REELHEIM port</dt><dd>{network.data.listener.port}</dd></dl>
        <p className="notice" data-testid="network-ready">{!lan.enabled ? "Paired devices are blocked while device access is off."
          : !lan.pin_configured ? "Set an access PIN before pairing devices."
          : network.data.listener.lan_reachable ? "The LAN listener is reachable from this host. Open a reachable address below on the other device."
          : "Device access is saved On, but no LAN listener was reachable. Start REELHEIM with Start.bat to apply it, then refresh. Check the Windows network and firewall if it is still unavailable."}</p>
        <div data-testid="lan-addresses">{network.data.addresses.map(address => <div className="network-address" key={address.url}>
          <code className="addr">{address.url}</code><span className="lm-fine">{address.reachable ? "Host listener reachable" : "Listener not reachable"}</span>
        </div>)}</div>
        {network.data.addresses.length === 0 && <p className="lm-fine">No private LAN address was found. Connect this PC to your home network in Windows.</p>}
        <button className="hbtn" aria-disabled={pending || network.loading || undefined} onClick={() => {
          if (!pending && !network.loading) void Promise.all([network.reload(), onReload(), devices.reload()]);
        }} data-testid="network-refresh">Refresh connection status</button>
      </div>}
      <form className="pin-form" data-nav-row onSubmit={(e) => { e.preventDefault(); savePin(); }}>
        <KeyRound size={24} />
        <input inputMode="numeric" autoComplete="new-password" type="password" value={pin} maxLength={32} readOnly={pending}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
          placeholder={lan.pin_configured ? "New PIN (8+ digits)" : "Set a PIN (8+ digits)"} aria-label="Access PIN" data-testid="pin-input" />
        <button type="submit" className="btn" disabled={pin.length < 8} aria-disabled={pending || undefined} data-testid="pin-save-button">
          {lan.pin_configured ? "Change PIN" : "Save PIN"}
        </button>
        <span className="muted" data-testid="pin-status">{lan.pin_configured ? "PIN is set" : "No PIN set yet"}</span>
      </form>
      {pending && <p role="status" data-testid="network-save-status">Saving network settings…</p>}
      {msg && <p className={msg.ok ? "form-ok" : "form-error"} role={msg.ok ? "status" : "alert"} data-testid="network-message">{msg.text}</p>}
      <h3>Paired devices</h3>
      <ResourceStatus loading={devices.loading && !devices.data} error={devices.error} onRetry={devices.reload} testId="network-devices-load" label="paired devices" />
      <div className="device-list" data-testid="device-list">
        {!devices.error && devices.data?.length === 0 && <p className="muted">No devices have paired yet.</p>}
        {devices.data?.map((d) => (
          <div key={d.id} className="device" data-testid={`device-item-${d.id}`}>
            {d.revoked ? <ShieldOff size={22} /> : <ShieldCheck size={22} className="ok" />}
            <strong>{d.name}</strong>
            <span className="muted">{d.last_ip ?? ""} · last seen {d.last_seen_at ? new Date(d.last_seen_at).toLocaleString() : "never"}</span>
            {d.revoked ? <span className="muted">revoked</span> : (
              <button className="btn btn--danger" aria-disabled={pending || undefined} onClick={() => revoke(d.id)} data-testid={`device-revoke-button-${d.id}`}>Revoke</button>
            )}
          </div>
        ))}
      </div>
      {network.data && <NetworkShares info={network.data} reload={network.reload} />}
    </section>
  );
}
