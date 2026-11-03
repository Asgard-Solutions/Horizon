import { Delete, Eraser, Space } from "lucide-react";
import { useEffect, useRef } from "react";

const LAST_KEY = "horizon.search.oskKey";

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
  const box = useRef<HTMLDivElement>(null);
  // Entering Search (from the top menu, "/" or Y) lands on the last-used key, or A the first time.
  useEffect(() => {
    if (!autofocus) return;
    const id = sessionStorage.getItem(LAST_KEY) ?? "osk-key-a";
    (box.current?.querySelector<HTMLElement>(`[data-testid="${id}"]`) ?? box.current?.querySelector<HTMLElement>(".osk-key"))?.focus({ preventScroll: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const onFocus = (e: React.FocusEvent) => { const id = (e.target as HTMLElement).dataset.testid; if (id?.startsWith("osk-key-")) sessionStorage.setItem(LAST_KEY, id); };
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return; // leave browser/OS shortcuts alone
    const t = e.target as HTMLElement;
    if (e.key === "ArrowRight" && t.matches(".osk-key") && !t.nextElementSibling) { if (onExitRight()) e.preventDefault(); }
    else if (e.key === "PadX" || e.key === "Backspace") { e.preventDefault(); onBackspace(); }
    else if (e.key === "PadY") { e.preventDefault(); onKey(" "); }
    else if (e.key.length === 1 && /[\p{L}\p{N} '\-.:&!?,]/u.test(e.key)) { e.preventDefault(); onKey(e.key); }
  };
  return (
    <div className="osk" ref={box} role="group" aria-label="On-screen keyboard" onKeyDown={onKeyDown} onFocus={onFocus} data-testid="osk">
      {ROWS.map((row) => (
        <div className="osk-row" key={row} data-nav-row data-nav-up={row === ROWS[0] ? '[data-testid="search-input"]' : undefined}>
          {[...row].map((ch) => (
            <button key={ch} className="osk-key" onClick={() => onKey(ch)}
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
