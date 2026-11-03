import { Delete, Lock } from "lucide-react";
import { useState } from "react";
import { post } from "../api";
import { useAuth } from "../App";

const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "clear", "0", "back"];

function defaultName() {
  const ua = navigator.userAgent;
  if (/Xbox/i.test(ua)) return "Xbox browser";
  if (/Android/i.test(ua)) return "Android device";
  if (/iPhone|iPad/i.test(ua)) return "iOS device";
  return "LAN browser";
}

export default function Pair() {
  const { auth, refresh } = useAuth();
  const [pin, setPin] = useState("");
  const [name, setName] = useState(defaultName());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const canPair = auth.lan_enabled && auth.pin_configured;

  const press = (k: string) => {
    if (k === "clear") setPin("");
    else if (k === "back") setPin((p) => p.slice(0, -1));
    else if (pin.length < 32) setPin((p) => p + k);
  };
  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await post("/api/auth/pair", { pin, device_name: name });
      refresh();
    } catch (e) {
      setError((e as Error).message);
      setPin("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="pair" data-testid="pair-page">
      <Lock size={48} className="pair-icon" />
      <h1>Connect to your media center</h1>
      {!canPair ? (
        <p className="pair-msg" data-testid="pair-blocked-message">{auth.message}</p>
      ) : (
        <>
          <p className="pair-msg">Enter the access PIN set on the host PC.</p>
          <div className="pin-dots" data-testid="pair-pin-display" aria-live="polite">
            {pin ? "•".repeat(pin.length) : <span className="muted">PIN</span>}
          </div>
          <div className="keypad" data-testid="pair-keypad">
            {KEYS.map((k, i) => (
              <button key={k} className="key" data-autofocus={i === 0 ? true : undefined} onClick={() => press(k)} data-testid={`pair-key-${k}`}
                aria-label={k === "back" ? "Delete digit" : k === "clear" ? "Clear" : k}>
                {k === "back" ? <Delete size={28} /> : k === "clear" ? "Clear" : k}
              </button>
            ))}
          </div>
          <label className="pair-name">
            Device name
            <input value={name} maxLength={60} onChange={(e) => setName(e.target.value)} data-testid="pair-device-name-input" />
          </label>
          <button className="btn btn--primary pair-submit" disabled={pin.length < 8 || busy || auth.locked_seconds > 0} onClick={submit}
            data-testid="pair-submit-button">
            {busy ? "Checking…" : "Pair this device"}
          </button>
          {error && <p className="form-error" role="alert" data-testid="pair-error">{error}</p>}
        </>
      )}
    </div>
  );
}
