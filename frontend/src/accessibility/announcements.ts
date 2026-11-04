/** One polite output channel. Only explicit actions/routes call it; never focus, timers or copied status DOM. */
export function createAnnouncer(write: (message: string) => void) {
  let enabled = false;
  let lastKey: string | undefined;
  let pending: ReturnType<typeof setTimeout> | undefined;
  const cancel = () => { clearTimeout(pending); pending = undefined; };
  return {
    setEnabled(value: boolean) {
      if (value === enabled) return;
      enabled = value; cancel(); lastKey = undefined; write("");
    },
    announce(message: string, key?: string) {
      if (!enabled || !message.trim() || (key !== undefined && key === lastKey)) return;
      cancel(); lastKey = key;
      write(""); // A fresh DOM change also permits repeating the test button's identical message.
      pending = setTimeout(() => { pending = undefined; write(message); }, 160);
    },
    dispose() { enabled = false; cancel(); lastKey = undefined; },
  };
}

export function routeAnnouncement(pathname: string, search: string) {
  const media = new URLSearchParams(search).get("media");
  const scope = media === "movie" ? "Movies: " : media === "tv" ? "TV Shows: " : "";
  let label = "REELHEIM Home";
  if (pathname === "/home/movie") label = "Movies Home";
  else if (pathname === "/home/tv") label = "TV Shows Home";
  else if (pathname === "/settings") label = "Settings";
  else if (pathname === "/discover") label = `${scope}Discover`;
  else if (pathname === "/atlas") label = `${scope}Library Atlas`;
  else if (pathname === "/search") label = `${scope}Search`;
  else if (pathname.startsWith("/movies/")) label = "Movie details";
  else if (pathname.startsWith("/shows/")) label = "TV show details";
  else if (pathname.startsWith("/play/")) label = "Media player";
  return { key: `route:${pathname}:${label}`, message: `${label} page.` };
}
