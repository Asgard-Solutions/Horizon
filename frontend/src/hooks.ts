import { useCallback, useEffect, useRef, useState } from "react";
import { pushBackHandler } from "./nav/spatial";

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    return fnRef
      .current()
      .then((d) => setData(d))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { reload(); }, deps);
  return { data, error, loading, reload, setData };
}

/** While `pending`, quietly re-fetches every few seconds (no loading state) until the server fills the data in. */
export function useQuietRefresh<T>(pending: boolean, version: unknown, fetcher: () => Promise<T>, apply: (d: T) => void, ms = 4000) {
  const tries = useRef(0);
  useEffect(() => {
    if (!pending || tries.current >= 45) return;
    const t = window.setTimeout(() => {
      tries.current += 1;
      fetcher().then(apply).catch(() => undefined);
    }, ms);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending, version]);
}

/** Registers a Back/Escape handler while mounted. Return false from the handler to pass Back further down. */
export function useBack(handler: () => boolean | void, active = true) {
  const ref = useRef(handler);
  ref.current = handler;
  useEffect(() => {
    if (!active) return;
    return pushBackHandler(() => ref.current());
  }, [active]);
}
