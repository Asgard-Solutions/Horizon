import { createContext, useContext, useEffect, useRef } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate, useNavigationType } from "react-router-dom";
import { api } from "./api";
import { useAsync } from "./hooks";
import { focusFirst, installNavigation, setFallbackBack } from "./nav/spatial";
import type { AuthStatus } from "./types";
import { PrimaryNav } from "./components/PrimaryNav";
import { Loading } from "./components/States";
import Home from "./pages/Home";
import Discover from "./pages/Discover";
import Atlas from "./pages/Atlas";
import Search from "./pages/Search";
import MovieDetail from "./pages/MovieDetail";
import ShowDetail from "./pages/ShowDetail";
import Player from "./pages/Player";
import Settings from "./pages/Settings";
import Pair from "./pages/Pair";
import { hubPath, scopedPath } from "./home/context";
import { useMediaType } from "./home/useMediaType";
import { useHomeLayout } from "./home/useHomeLayout";

export const AuthContext = createContext<{ auth: AuthStatus; refresh: () => void } | null>(null);
export const useAuth = () => useContext(AuthContext)!;

const routeFocus = new Map<string, { selector: string; scroll: number }>();

function NavBridge() {
  const navigate = useNavigate();
  const location = useLocation();
  const navigationType = useNavigationType();
  const mediaType = useMediaType();
  const priorPath = useRef(location.pathname);
  useEffect(() => installNavigation(), []);
  // "/" on a keyboard or Y on a controller opens Search from browse screens (never in text fields or the player).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || location.pathname === "/" || location.pathname.startsWith("/play/") || location.pathname === "/search") return;
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "/" || e.key === "PadY") { e.preventDefault(); navigate(scopedPath("/search", mediaType)); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [location.pathname, mediaType, navigate]);
  useEffect(() => {
    setFallbackBack(() => {
      if (location.pathname !== "/") {
        if ((window.history.state?.idx ?? 0) > 0) navigate(-1);
        else navigate(mediaType ? hubPath(mediaType) : "/");
      }
    });
  }, [location.pathname, mediaType, navigate]);
  useEffect(() => {
    const saved = navigationType === "POP" ? routeFocus.get(location.key) : null;
    if (priorPath.current !== location.pathname) window.scrollTo(0, 0);
    priorPath.current = location.pathname;
    const entryFocus = document.activeElement;
    // Content loads asynchronously; keep trying briefly until something inside <main> can take focus.
    let tries = 0;
    const t = window.setInterval(() => {
      if (saved && !location.pathname.startsWith("/play/")) {
        const target = document.querySelector<HTMLElement>(saved.selector);
        if (target) { target.focus({ preventScroll: true }); window.scrollTo(0, saved.scroll); return window.clearInterval(t); }
      }
      const active = document.activeElement;
      if (navigationType !== "POP" && active === entryFocus && active?.closest("header")) focusFirst(document.querySelector("main"));
      if (tries++ > 20 || (active && active !== document.body)) return window.clearInterval(t);
      focusFirst(document.querySelector("main"));
    }, 100);
    const remember = (event: FocusEvent) => {
      const element = event.target as HTMLElement;
      const selector = element.id ? `#${CSS.escape(element.id)}` : element.dataset.testid ? `[data-testid="${CSS.escape(element.dataset.testid)}"]` : null;
      if (selector && !element.closest("[data-nav-scope='modal']")) routeFocus.set(location.key, { selector, scroll: window.scrollY });
      if (routeFocus.size > 100) routeFocus.delete(routeFocus.keys().next().value!);
    };
    document.addEventListener("focusin", remember);
    const rememberScroll = () => {
      const current = routeFocus.get(location.key);
      if (current) routeFocus.set(location.key, { ...current, scroll: window.scrollY });
    };
    window.addEventListener("scroll", rememberScroll, { passive: true });
    return () => { window.clearInterval(t); document.removeEventListener("focusin", remember); window.removeEventListener("scroll", rememberScroll); };
  }, [location.key, location.pathname, navigationType]);
  return null;
}

function Shell() {
  const { pathname } = useLocation();
  const mediaType = useMediaType();
  const layout = useHomeLayout();
  const inPlayer = pathname.startsWith("/play/");
  const home = pathname === "/" || pathname.startsWith("/home/");
  return (
    <div className={inPlayer ? "shell shell--player" : home ? `shell home-shell${pathname === "/" ? " home-shell--selection" : ""}${layout.compact ? " home-shell--compact" : ""}${layout.stackedHome ? " home-shell--stacked-home" : ""}${layout.stackedHub ? " home-shell--stacked-hub" : ""}` : pathname === "/settings" ? "shell shell--settings" : "shell"}>
      {!inPlayer && <PrimaryNav />}
      <main className="main" data-testid="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/home/:mediaType" element={<Home />} />
          <Route path="/discover" element={<Discover key={mediaType ?? "all"} />} />
          <Route path="/atlas" element={<Atlas key={mediaType ?? "all"} />} />
          <Route path="/search" element={<Search key={mediaType ?? "all"} />} />
          <Route path="/movies" element={<Navigate to="/discover?view=movies" replace />} />
          <Route path="/movies/:id" element={<MovieDetail />} />
          <Route path="/shows" element={<Navigate to="/discover?view=shows" replace />} />
          <Route path="/shows/:id" element={<ShowDetail />} />
          <Route path="/play/:fileId" element={<Player />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/sources" element={<Navigate to={scopedPath("/settings?section=libraries", mediaType)} replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  const { data: auth, error, reload } = useAsync(() => api<AuthStatus>("/api/auth/status"), []);
  if (error) return <div className="fatal" data-testid="server-unreachable">Cannot reach the media server: {error}</div>;
  if (!auth) return <Loading label="Connecting to media server" />;
  return (
    <AuthContext.Provider value={{ auth, refresh: reload }}>
      <BrowserRouter>
        <NavBridge />
        {auth.role === "none" ? <Pair /> : <Shell />}
      </BrowserRouter>
    </AuthContext.Provider>
  );
}
