import { Accessibility, Film, Gamepad2, Info, Library, LogOut, Monitor, Network, Rows3, type LucideIcon } from "lucide-react";
import { useRef, type KeyboardEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { api, post } from "../api";
import { useAuth } from "../App";
import { PageHeader } from "../components/States";
import { useAsync, useBack } from "../hooks";
import { focusables } from "../nav/spatial";
import { AccessibilitySection } from "../settings/AccessibilitySection";
import { CollectionsSection } from "../settings/CollectionsSection";
import { DisplaySection } from "../settings/DisplaySection";
import { InputSection } from "../settings/InputSection";
import { LibraryManager } from "../settings/library/LibraryManager";
import { NetworkSection } from "../settings/NetworkSection";
import { PlaybackSection } from "../settings/PlaybackSection";
import { SectionHead } from "../settings/ui";
import { SystemSection } from "../settings/SystemSection";
import type { SystemInfo } from "../types";

type Cat = { id: string; label: string; icon: LucideIcon; host?: boolean; device?: boolean };
const CATS: Cat[] = [
  { id: "libraries", label: "Libraries & scanning", icon: Library, host: true },
  { id: "device", label: "This device", icon: LogOut, device: true },
  { id: "playback", label: "Playback", icon: Film },
  { id: "collections", label: "Collections & folders", icon: Rows3, host: true },
  { id: "display", label: "Appearance & 4K scaling", icon: Monitor },
  { id: "accessibility", label: "Motion & accessibility", icon: Accessibility },
  { id: "input", label: "Controller & keyboard", icon: Gamepad2 },
  { id: "network", label: "Network & devices", icon: Network, host: true },
  { id: "system", label: "System & diagnostics", icon: Info },
];

function DeviceSection() {
  const { auth, refresh } = useAuth();
  return (
    <div className="ssection" data-testid="settings-device">
      <SectionHead title="This device" intro={<>Paired as <strong>{auth.device_name}</strong>. Library folders and network settings can only be changed on the host PC.</>} />
      <button className="hbtn btn--danger" onClick={() => post("/api/auth/logout").then(refresh)} data-testid="device-unpair-button">
        <LogOut size={22} /> Unpair this device
      </button>
    </div>
  );
}

const RAIL_SEL = '[data-testid="settings-rail"] [aria-current="true"]';

/** Two-column, controller-first Settings: categories on the left (selection follows focus), options on the right. */
export default function Settings() {
  const { auth } = useAuth();
  const host = auth.role === "host";
  const cats = CATS.filter((c) => (host ? !c.device : !c.host));
  const [params, setParams] = useSearchParams();
  const section = cats.find((c) => c.id === params.get("section"))?.id ?? cats[0].id;
  const system = useAsync(() => (host ? api<SystemInfo>("/api/system") : Promise.resolve(null)), [host]);
  const panel = useRef<HTMLDivElement>(null);
  const lastInPanel = useRef<Record<string, HTMLElement | null>>({});

  const select = (id: string) => { if (id !== section) { const next = new URLSearchParams(params); next.set("section", id); setParams(next, { replace: true }); } };
  const enterPanel = () => {
    const remembered = lastInPanel.current[section];
    const target = remembered && panel.current?.contains(remembered) ? remembered : focusables().find((el) => panel.current?.contains(el));
    target?.focus({ preventScroll: false });
    return !!target;
  };
  const railKey = (e: KeyboardEvent) => { if (e.key === "ArrowRight" && enterPanel()) e.preventDefault(); };
  // Left from the first control of a row (or a control at the panel's left edge) returns to the selected category.
  const panelKey = (e: KeyboardEvent) => {
    if (e.key !== "ArrowLeft" || e.defaultPrevented) return;
    const el = document.activeElement as HTMLElement;
    if (el instanceof HTMLInputElement && el.selectionStart) return;
    const row = el.closest("[data-nav-row]");
    const first = row ? focusables().find((x) => row.contains(x)) === el : el.getBoundingClientRect().left - (panel.current?.getBoundingClientRect().left ?? 0) < 48;
    if (!first) return;
    e.preventDefault();
    document.querySelector<HTMLElement>(RAIL_SEL)?.focus();
  };
  // B inside the options returns to the category list first; B on the list leaves Settings.
  useBack(() => {
    if (!panel.current?.contains(document.activeElement)) return false;
    document.querySelector<HTMLElement>(RAIL_SEL)?.focus();
  });

  return (
    <div className="page settings" data-testid="settings-page">
      <PageHeader title="Settings" meta={host ? "Host PC" : `Paired device · ${auth.device_name ?? ""}`} />
      <div className="settings-layout">
        <nav className="settings-rail" aria-label="Settings categories" data-nav-prefer-selected onKeyDown={railKey} data-testid="settings-rail">
          {cats.map((c) => (
            <button key={c.id} className="settings-cat" aria-current={c.id === section} data-autofocus={c.id === section ? true : undefined}
              onFocus={() => select(c.id)} onClick={() => { select(c.id); window.setTimeout(enterPanel, 0); }} data-testid={`settings-cat-${c.id}`}>
              <c.icon size={24} aria-hidden="true" /><span>{c.label}</span>
            </button>
          ))}
        </nav>
        <div className="settings-panel" ref={panel} onKeyDown={panelKey} data-testid="settings-panel"
          onFocus={(e) => { lastInPanel.current[section] = e.target as HTMLElement; }}>
          {section === "libraries" && <LibraryManager />}
          {section === "device" && <DeviceSection />}
          {section === "playback" && <PlaybackSection />}
          {section === "collections" && <CollectionsSection />}
          {section === "display" && <DisplaySection />}
          {section === "accessibility" && <AccessibilitySection />}
          {section === "input" && <InputSection />}
          {section === "network" && system.data && (
            <div className="ssection"><NetworkSection system={system.data} onChange={system.setData} /></div>
          )}
          {section === "system" && <SystemSection system={system.data} />}
        </div>
      </div>
    </div>
  );
}
