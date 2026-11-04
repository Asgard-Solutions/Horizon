import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { parseMediaType, type MediaType } from "./context";

export function useMediaType(): MediaType | null {
  const { pathname, search } = useLocation();
  const explicit = parseMediaType(new URLSearchParams(search).get("media"))
    ?? parseMediaType(pathname.match(/^\/home\/(movie|tv)$/)?.[1] ?? null)
    ?? (pathname.startsWith("/movies/") ? "movie" : pathname.startsWith("/shows/") ? "tv" : null);
  let saved: MediaType | null = null;
  try { saved = parseMediaType(sessionStorage.getItem("horizon.mediaType")); } catch {}
  useEffect(() => {
    if (explicit) try { sessionStorage.setItem("horizon.mediaType", explicit); } catch {}
  }, [explicit]);
  return explicit ?? saved;
}
