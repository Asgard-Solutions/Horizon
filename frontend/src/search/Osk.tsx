import { Delete, Eraser, Space } from "lucide-react";

const ROWS = ["abcdef", "ghijkl", "mnopqr", "stuvwx", "yz1234", "567890", "'-.:&!"];
const NAMES: Record<string, string> = { "'": "Apostrophe", "-": "Hyphen", ".": "Period", ":": "Colon", "&": "Ampersand", "!": "Exclamation mark" };
const ID: Record<string, string> = { "'": "apostrophe", "-": "hyphen", ".": "period", ":": "colon", "&": "ampersand", "!": "exclamation" };

interface Props {
  onKey: (ch: string) => void;
  onBackspace: () => void;
  onClear: () => void;
  onExitRight: () => boolean;
  autofocus: boolean;
}

/** D-pad friendly on-screen keyboard. X = backspace, Y = space on a controller; physical typing always works too. */
export function Osk({ onKey, onBackspace, onClear, onExitRight, autofocus }: Props) {
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return; // leave browser/OS shortcuts alone
    const t = e.target as HTMLElement;
    if (e.key === "ArrowRight" && t.matches(".osk-key") && !t.nextElementSibling) { if (onExitRight()) e.preventDefault(); }
    else if (e.key === "PadX" || e.key === "Backspace") { e.preventDefault(); onBackspace(); }
    else if (e.key === "PadY") { e.preventDefault(); onKey(" "); }
    else if (e.key.length === 1 && /[\p{L}\p{N} '\-.:&!?,]/u.test(e.key)) { e.preventDefault(); onKey(e.key); }
  };
  return (
    <div className="osk" role="group" aria-label="On-screen keyboard" onKeyDown={onKeyDown} data-testid="osk">
      {ROWS.map((row, r) => (
        <div className="osk-row" key={row} data-nav-row>
          {[...row].map((ch, c) => (
            <button key={ch} className="osk-key" onClick={() => onKey(ch)} data-autofocus={autofocus && r === 0 && c === 0 ? true : undefined}
              data-testid={`osk-key-${ID[ch] ?? ch}`} aria-label={NAMES[ch] ?? ch.toUpperCase()}>{ch.toUpperCase()}</button>
          ))}
        </div>
      ))}
      <div className="osk-row osk-row--wide" data-nav-row>
        <button className="osk-key osk-key--wide" onClick={() => onKey(" ")} data-testid="osk-key-space" aria-label="Space"><Space size={20} /> Space</button>
        <button className="osk-key" onClick={onBackspace} data-testid="osk-key-backspace" aria-label="Backspace"><Delete size={20} /></button>
        <button className="osk-key" onClick={onClear} data-testid="osk-key-clear" aria-label="Clear"><Eraser size={20} /></button>
      </div>
      <p className="osk-hint" aria-hidden="true"><kbd>X</kbd> delete · <kbd>Y</kbd> space · <kbd>→</kbd> results</p>
    </div>
  );
}
