import { Link, useLocation } from "react-router-dom";
import type { KeyboardEvent } from "react";
import { ArrowLeft, Settings } from "lucide-react";
import { goBack } from "../nav/spatial";
import { scopedPath } from "../home/context";
import { useMediaType } from "../home/useMediaType";
import { useHomeLayout } from "../home/useHomeLayout";
import logo from "../assets/reelheim-logo-header-1120.png";

export function PrimaryNav() {
  const { pathname } = useLocation();
  const type = useMediaType();
  const { stackedHome: wrapped } = useHomeLayout();
  const home = pathname === "/" || pathname.startsWith("/home/");
  const moveInHeader = (event: KeyboardEvent) => {
    if (!home || !event.key.startsWith("Arrow")) return;
    const current = (event.target as HTMLElement).id;
    const last = document.querySelector<HTMLElement>("[data-home-last-focus]")?.dataset.homeLastFocus;
    let target = current;
    if (event.key === "ArrowDown") target = wrapped && current === "global-home" ? "global-settings" : last ?? (pathname === "/" ? "home-movies" : "hub-atlas");
    if (event.key === "ArrowUp" && wrapped && current !== "global-home") target = "global-home";
    if (event.key === "ArrowLeft") target = current === "global-settings" && !wrapped ? "global-home" : current;
    if (event.key === "ArrowRight") target = current === "global-home" && !wrapped ? "global-settings" : current;
    document.getElementById(target)?.focus({ preventScroll: false });
    event.preventDefault();
  };
  return <header className={home ? "hub-header" : "hub-header hub-header--browse"} data-testid="primary-nav" onKeyDown={moveInHeader}>
    <Link className="hub-brand" to="/" id="global-home" aria-label="REELHEIM Home" data-testid="nav-home"><img src={logo} alt="REELHEIM Media Center" /></Link>
    {!home && <button className="hub-global-back" onClick={goBack} data-testid="nav-back"><ArrowLeft aria-hidden="true" focusable="false" />Back</button>}
    {pathname !== "/settings" && <nav aria-label="Global utilities">
      <Link className="hub-utility hub-settings" to={scopedPath("/settings", type)} id="global-settings" data-testid="nav-settings"><Settings aria-hidden="true" focusable="false" /><span>Settings</span></Link>
    </nav>}
  </header>;
}
