import { createContext, useContext, useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api } from "./api";
import { useAsync } from "./hooks";
import { focusFirst, installNavigation, setFallbackBack } from "./nav/spatial";
import type { AuthStatus } from "./types";
import { Sidebar } from "./components/Sidebar";
import { Loading } from "./components/States";
import Home from "./pages/Home";
import Movies from "./pages/Movies";
import MovieDetail from "./pages/MovieDetail";
import Shows from "./pages/Shows";
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
      {!inPlayer && <Sidebar />}
      <main className="main" data-testid="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/movies" element={<Movies />} />
          <Route path="/movies/:id" element={<MovieDetail />} />
          <Route path="/shows" element={<Shows />} />
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
