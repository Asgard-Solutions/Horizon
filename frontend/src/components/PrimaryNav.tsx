import { NavLink } from "react-router-dom";
import { useAuth } from "../App";
import { Wordmark } from "./HorizonMark";

/** Top shell navigation. Only real destinations; Search arrives in Stage 2 and is not shown until it works. */
export function PrimaryNav() {
  const { auth } = useAuth();
  const items = [
    { to: "/", label: "Home", id: "home" },
    { to: "/discover", label: "Discover", id: "discover" },
    { to: "/atlas", label: "Atlas", id: "atlas" },
    { to: "/search", label: "Search", id: "search" },
    { to: "/settings", label: auth.role === "host" ? "Library" : "This device", id: "settings" },
  ];
  return (
    <header className="topnav" data-testid="primary-nav">
      <Wordmark />
      <nav aria-label="Main">
        <ul>
          {items.map((i) => (
            <li key={i.to}>
              <NavLink to={i.to} end={i.to === "/"} className="topnav-link" data-testid={`nav-${i.id}`}>
                {i.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <span className="topnav-role" data-testid="nav-role">
        {auth.role === "host" ? "Host PC" : `Paired · ${auth.device_name ?? "device"}`}
      </span>
    </header>
  );
}
