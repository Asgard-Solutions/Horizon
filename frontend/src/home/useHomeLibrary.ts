import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { HomeData } from "../types";
import type { MediaType } from "./context";

const cache = new Map<string, HomeData>();

export function useHomeLibrary(type: MediaType | null) {
  const key = type ?? "selection";
  const [data, setData] = useState<HomeData | null>(() => cache.get(key) ?? null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision(value => value + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setData(cache.get(key) ?? null);
    setLoading(true);
    api<HomeData>(`/api/home${type ? `?media_type=${type}` : ""}`, { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted) { cache.set(key, value); setData(value); setError(null); } })
      .catch((failure: Error) => { if (!controller.signal.aborted) setError(failure.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [key, type, revision]);
  useEffect(() => {
    const timer = window.setInterval(reload, 15000);
    window.addEventListener("focus", reload);
    return () => { window.clearInterval(timer); window.removeEventListener("focus", reload); };
  }, [reload]);
  return { data, error, loading, reload };
}
