import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { getAnnouncementsPref, subscribeAppearancePrefs } from "../theme/appearancePrefs";
import { createAnnouncer, routeAnnouncement } from "./announcements";

type Announce = (message: string, key?: string) => void;
const AnnouncementContext = createContext<Announce>(() => {});
export const useAnnounce = () => useContext(AnnouncementContext);

/** Always mounted and initially empty so assistive technology can observe later text changes. */
export function AnnouncementProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState("");
  const [announcer] = useState(() => createAnnouncer(setMessage));
  useEffect(() => {
    const sync = () => announcer.setEnabled(getAnnouncementsPref());
    sync();
    const unsubscribe = subscribeAppearancePrefs(sync);
    return () => { unsubscribe(); announcer.dispose(); };
  }, [announcer]);
  return <AnnouncementContext.Provider value={announcer.announce}>
    <div className="a11y-live-region" role="status" aria-live="polite" aria-atomic="true" aria-relevant="additions text" data-testid="screen-reader-announcements">{message}</div>
    {children}
  </AnnouncementContext.Provider>;
}

export function RouteAnnouncements() {
  const location = useLocation();
  const announce = useAnnounce();
  const context = routeAnnouncement(location.pathname, location.search);
  useEffect(() => {
    // Child effects can run before the provider subscribes. Defer until the empty region is mounted.
    const timer = window.setTimeout(() => announce(context.message, context.key), 0);
    return () => window.clearTimeout(timer);
  }, [announce, context.key, context.message]);
  return null;
}
