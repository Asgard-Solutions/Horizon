import { KeyRound, ShieldCheck, ShieldOff, Wifi, WifiOff } from "lucide-react";
import { useState } from "react";
import { api, del, post } from "../api";
import { useAsync } from "../hooks";
import type { Device, SystemInfo } from "../types";

export function NetworkSection({ system, onChange }: { system: SystemInfo; onChange: (s: SystemInfo) => void }) {
  const devices = useAsync(() => api<Device[]>("/api/devices"), []);
  const [pin, setPin] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const lan = system.lan;

  const savePin = async () => {
    try {
      const r = await post<{ revoked_devices: number }>("/api/settings/pin", { pin, revoke_devices: true });
      setPin("");
      setMsg({ ok: true, text: `PIN saved.${r.revoked_devices ? ` ${r.revoked_devices} paired device(s) must pair again.` : ""}` });
      onChange({ ...system, lan: { ...lan, pin_configured: true } });
      devices.reload();
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  };
  const toggleLan = async () => {
    try {
      onChange(await post<SystemInfo>("/api/settings/lan", { enabled: !lan.enabled }));
      setMsg(null);
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  };
  const revoke = async (id: number) => {
    await del(`/api/devices/${id}`).catch(() => undefined);
    devices.reload();
  };

  return (
    <section className="panel" data-testid="settings-network">
      <h2>Network access</h2>
      <p className="muted">Off by default. When on, other devices on your private home network (for example the Xbox browser) can open the library after entering the PIN. The server never configures your router and refuses connections from public internet addresses.</p>
      <div className="lan-status" data-testid="lan-status">
        {lan.enabled ? <Wifi size={28} className="ok" /> : <WifiOff size={28} />}
        <strong data-testid="lan-status-text">LAN access is {lan.enabled ? "ON" : "OFF"}</strong>
        <button className={lan.enabled ? "btn btn--danger" : "btn btn--primary"} onClick={toggleLan} disabled={!lan.pin_configured && !lan.enabled}
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
      {lan.enabled && lan.addresses.length > 0 && (
        <div data-testid="lan-addresses">
          <span className="muted">Open one of these on the other device:</span>
          {lan.addresses.map((a) => <code key={a} className="addr">{a}</code>)}
        </div>
      )}
      <form className="pin-form" onSubmit={(e) => { e.preventDefault(); savePin(); }}>
        <KeyRound size={24} />
        <input inputMode="numeric" autoComplete="new-password" type="password" value={pin} maxLength={32}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
          placeholder={lan.pin_configured ? "New PIN (8+ digits)" : "Set a PIN (8+ digits)"} aria-label="Access PIN" data-testid="pin-input" />
        <button type="submit" className="btn" disabled={pin.length < 8} data-testid="pin-save-button">
          {lan.pin_configured ? "Change PIN" : "Save PIN"}
        </button>
        <span className="muted" data-testid="pin-status">{lan.pin_configured ? "PIN is set" : "No PIN set yet"}</span>
      </form>
      {msg && <p className={msg.ok ? "form-ok" : "form-error"} role="status" data-testid="network-message">{msg.text}</p>}
      <h3>Paired devices</h3>
      <div className="device-list" data-testid="device-list">
        {devices.data?.length === 0 && <p className="muted">No devices have paired yet.</p>}
        {devices.data?.map((d) => (
          <div key={d.id} className="device" data-testid={`device-item-${d.id}`}>
            {d.revoked ? <ShieldOff size={22} /> : <ShieldCheck size={22} className="ok" />}
            <strong>{d.name}</strong>
            <span className="muted">{d.last_ip ?? ""} · last seen {d.last_seen_at ? new Date(d.last_seen_at).toLocaleString() : "never"}</span>
            {d.revoked ? <span className="muted">revoked</span> : (
              <button className="btn btn--danger" onClick={() => revoke(d.id)} data-testid={`device-revoke-button-${d.id}`}>Revoke</button>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
