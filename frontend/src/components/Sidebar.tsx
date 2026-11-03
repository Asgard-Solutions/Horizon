import { Clapperboard, Film, House, Settings, Tv } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../App";

const ITEMS = [
  { to: "/", label: "Home", icon: House, id: "home" },
  { to: "/movies", label: "Movies", icon: Film, id: "movies" },
  { to: "/shows", label: "TV Shows", icon: Tv, id: "shows" },
  { to: "/settings", label: "Settings", icon: Settings, id: "settings" },
];

export function Sidebar() {
  const { auth } = useAuth();
  return (
    <nav className="sidebar" aria-label="Main" data-testid="sidebar-nav">
      <div className="brand" data-testid="brand">
        <Clapperboard size={30} strokeWidth={2.2} />
        <span>Open<br />Media</span>
      </div>
      <ul>
        {ITEMS.map(({ to, label, icon: Icon, id }) => (
          <li key={to}>
            <NavLink to={to} end={to === "/"} className="side-link" data-testid={`nav-${id}`}>
              <Icon size={26} />
              <span>{label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
      <div className="side-foot" data-testid="sidebar-role">
        {auth.role === "host" ? "Host PC" : `Paired: ${auth.device_name ?? "device"}`}
      </div>
    </nav>
  );
}
