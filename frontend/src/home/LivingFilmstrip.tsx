import { LayoutGrid, Rows3 } from "lucide-react";
import { useEffect, useLayoutEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { TitleArt } from "../components/TitleArt";
import { progressRatio } from "../format";
import type { FilmGroup, StageItem } from "./adapter";

interface Props {
  groups: FilmGroup[];
  group: FilmGroup;
  onGroup: (id: FilmGroup["id"]) => void;
  selectedKey: string;
  onSelect: (item: StageItem) => void;
  view: "strip" | "grid";
  onView: (v: "strip" | "grid") => void;
  restoreKey: string | null;
  onAnchor: (x: number | null) => void;
}

const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** The Living Filmstrip: one real-data rail with a gentle curve, or an ordinary grid (remembered locally). */
export function LivingFilmstrip({ groups, group, onGroup, selectedKey, onSelect, view, onView, restoreKey, onAnchor }: Props) {
  const navigate = useNavigate();
  const track = useRef<HTMLDivElement>(null);
  const index = Math.max(0, group.items.findIndex((i) => i.key === selectedKey));

  // Keep the focused card in a stable zone near the centre; edges stop (no wrap).
  useLayoutEffect(() => {
    const el = track.current;
    const card = el?.querySelector<HTMLElement>(`[data-key="${CSS.escape(selectedKey)}"]`);
    if (!el || !card || view !== "strip") return;
    const left = card.offsetLeft - (el.clientWidth - card.offsetWidth) / 2;
    el.scrollTo({ left: Math.max(0, left), behavior: reduced() ? "auto" : "smooth" });
  }, [selectedKey, view, group.id]);

  // Report the focused card's centre for the Horizon Line.
  useEffect(() => {
    const el = track.current;
    if (!el) return;
    const report = () => {
      const card = el.querySelector<HTMLElement>(`[data-key="${CSS.escape(selectedKey)}"]`);
      const host = el.closest(".home")?.getBoundingClientRect();
      if (!card || !host || view !== "strip") return onAnchor(null);
      const r = card.getBoundingClientRect();
      onAnchor(r.left + r.width / 2 - host.left);
    };
    report();
    el.addEventListener("scroll", report, { passive: true });
    window.addEventListener("resize", report);
    return () => { el.removeEventListener("scroll", report); window.removeEventListener("resize", report); };
  }, [selectedKey, view, group.id, onAnchor]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "PageUp" && e.key !== "PageDown") return;
      const i = groups.findIndex((g) => g.id === group.id) + (e.key === "PageDown" ? 1 : -1);
      if (i < 0 || i >= groups.length) return;
      e.preventDefault();
      const inside = !!track.current?.contains(document.activeElement);
      onGroup(groups[i].id);
      // Keep a controller user's place: if focus was in the strip, move it to the new group's first card.
      if (inside) window.setTimeout(() => track.current?.querySelector<HTMLElement>(".film")?.focus({ preventScroll: true }), 0);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [groups, group.id, onGroup]);

  return (
    <section className={`filmstrip filmstrip--${view}`} aria-label="Browse your library" data-testid="living-filmstrip">
      <div className="filmstrip-head" data-nav-up='[data-testid="stage-primary-action"]'>
        <div className="filmstrip-groups" role="tablist" aria-label="Groups" data-nav-prefer-selected>
          {groups.map((g) => (
            <button key={g.id} role="tab" aria-selected={g.id === group.id} className={g.id === group.id ? "gtab gtab--active" : "gtab"}
              onClick={() => onGroup(g.id)} onFocus={() => g.id !== group.id && onGroup(g.id)}
              data-testid={`filmstrip-group-${g.id}`}>
              {g.label} <span className="gtab-count">{g.items.length}</span>
            </button>
          ))}
        </div>
        <button className="hbtn hbtn--quiet" onClick={() => onView(view === "strip" ? "grid" : "strip")} data-testid="filmstrip-view-toggle"
          aria-label={view === "strip" ? "Switch to grid view" : "Switch to filmstrip view"}>
          {view === "strip" ? <LayoutGrid size={20} /> : <Rows3 size={20} />}
          {view === "strip" ? "Grid view" : "Filmstrip view"}
        </button>
      </div>
      <div className="filmstrip-track" ref={track} data-nav-noscroll={view === "strip" || undefined} data-nav-row={view === "strip" || undefined} data-nav-prefer-selected role="list" data-testid="filmstrip-track">
        {group.items.map((item, i) => {
          const d = i - index;
          const ratio = progressRatio(item.progress);
          return (
            <div role="listitem" key={item.key} className="film-slot">
              <button
                className={item.key === selectedKey ? "film film--selected" : "film"}
                data-key={item.key}
                aria-current={item.key === selectedKey ? "true" : undefined}
                data-autofocus={item.key === restoreKey || undefined}
                style={{ "--dist": Math.min(Math.abs(d), 5), "--side": Math.sign(d) } as React.CSSProperties}
                onFocus={() => onSelect(item)}
                onMouseEnter={() => onSelect(item)}
                onClick={() => navigate(item.kind === "show" ? item.primary.to : item.details ?? item.primary.to)}
                aria-label={`${item.title}${item.subtitle ? `, ${item.subtitle}` : ""}. ${item.chips.join(", ")}`}
                data-testid={`film-card-${item.key}`}
              >
                <span className="film-art">
                  <TitleArt image={item.poster} title={item.title} kind={item.kind} />
                  {ratio > 0 && !item.progress?.watched && <span className="film-progress"><span style={{ width: `${ratio * 100}%` }} /></span>}
                  {item.progress?.watched && <span className="film-watched">Watched</span>}
                </span>
                <span className="film-label">
                  <span className="film-title">{item.title}</span>
                  {item.subtitle && <span className="film-sub">{item.subtitle}</span>}
                </span>
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}
