import { Gamepad2, Keyboard } from "lucide-react";
import { useEffect, useState } from "react";
import { SectionHead } from "./ui";

const PAD: [string, string][] = [
  ["D-pad / left stick", "Move focus"], ["A", "Select / play"], ["B", "Back (closes panels first)"], ["X", "Delete a letter in Search"],
  ["Y", "Open Search"], ["LB / RB", "Previous / next page (Atlas)"], ["Menu", "Play / pause"],
];
const KEYS: [string, string][] = [
  ["Arrow keys", "Move focus"], ["Enter", "Select / play"], ["Esc / Backspace", "Back"], ["/", "Open Search"],
  ["Page Up / Page Down", "Previous / next page (Atlas)"], ["Space or K", "Play / pause (player)"], ["Left / Right", "Skip back / forward (player)"],
  ["F", "Full screen (player)"], ["M", "Mute (player)"],
];

function useGamepads() {
  const read = () => Array.from(navigator.getGamepads?.() ?? []).filter((p): p is Gamepad => !!p).map((p) => p.id);
  const [pads, setPads] = useState<string[]>(read);
  useEffect(() => {
    const on = () => setPads(read());
    window.addEventListener("gamepadconnected", on);
    window.addEventListener("gamepaddisconnected", on);
    const t = window.setInterval(on, 2000);
    return () => { window.removeEventListener("gamepadconnected", on); window.removeEventListener("gamepaddisconnected", on); window.clearInterval(t); };
  }, []);
  return pads;
}

function Map({ rows, testId }: { rows: [string, string][]; testId: string }) {
  return <dl className="sfacts sfacts--map" tabIndex={0} data-nav data-testid={testId}>{rows.map(([k, v]) => <div key={k}><dt><kbd>{k}</kbd></dt><dd>{v}</dd></div>)}</dl>;
}

/** Controller & keyboard reference. The mapping is fixed in this version, so nothing here pretends to be editable. */
export function InputSection() {
  const pads = useGamepads();
  const api = typeof navigator.getGamepads === "function";
  return (
    <div className="ssection" data-testid="settings-input">
      <SectionHead title="Controller & keyboard" intro="Controllers, keyboards and TV remotes all work at once; switch any time. Button mapping is fixed in this version." />
      <p className="lm-facts" data-testid="input-gamepads">
        <Gamepad2 size={22} aria-hidden="true" />{" "}
        {!api ? "This browser does not offer controller access." : pads.length ? `Connected: ${pads.join(", ")}` : "No controller detected. Press any button on a connected controller."}
      </p>
      <h3 className="ssub"><Gamepad2 size={20} aria-hidden="true" /> Controller</h3>
      <Map rows={PAD} testId="input-pad-map" />
      <h3 className="ssub"><Keyboard size={20} aria-hidden="true" /> Keyboard</h3>
      <Map rows={KEYS} testId="input-key-map" />
      <p className="lm-fine">Typing on a physical keyboard in Search goes straight into the search box, and the on-screen keyboard stays visible.</p>
    </div>
  );
}
