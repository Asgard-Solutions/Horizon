import { createContext, useContext, useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
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

export const AuthContext = createContext<{ auth: AuthStatus; refresh: () => void } | null>(null);
export const useAuth = () => useContext(AuthContext)!;

function NavBridge() {
  const navigate = useNavigate();
  const location = useLocation();
  useEffect(() => installNavigation(), []);
  // "/" on a keyboard or Y on a controller opens Search from browse screens (never in text fields or the player).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || location.pathname.startsWith("/play/") || location.pathname === "/search") return;
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "/" || e.key === "PadY") { e.preventDefault(); navigate("/search"); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [location.pathname, navigate]);
  useEffect(() => {
    setFallbackBack(() => {
      if (location.pathname !== "/") navigate(-1);
    });
  }, [location.pathname, navigate]);
  useEffect(() => {
    window.scrollTo(0, 0);
    // Content loads asynchronously; keep trying briefly until something inside <main> can take focus.
    let tries = 0;
    const t = window.setInterval(() => {
      const active = document.activeElement;
      if (tries++ > 20 || (active && active !== document.body)) return window.clearInterval(t);
      focusFirst(document.querySelector("main"));
    }, 100);
    return () => window.clearInterval(t);
  }, [location.pathname]);
  return null;
}

function Shell() {
  const { pathname } = useLocation();
  const inPlayer = pathname.startsWith("/play/");
  return (
    <div className={inPlayer ? "shell shell--player" : "shell"}>
      {!inPlayer && <PrimaryNav />}
      <main className="main" data-testid="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/discover" element={<Discover />} />
          <Route path="/atlas" element={<Atlas />} />
          <Route path="/search" element={<Search />} />
          <Route path="/movies" element={<Navigate to="/discover?view=movies" replace />} />
          <Route path="/movies/:id" element={<MovieDetail />} />
          <Route path="/shows" element={<Navigate to="/discover?view=shows" replace />} />
          <Route path="/shows/:id" element={<ShowDetail />} />
          <Route path="/play/:fileId" element={<Player />} />
          <Route path="/settings" element={<Settings />} />
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
