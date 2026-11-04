import { useEffect, useRef, type RefObject } from "react";
import { clearNfoDraft, setNfoDraft } from "./NfoNavigationPrompt";

/** The always-mounted route blocker protects drafts while Settings Activity panels are hidden. */
export function useNfoLeaveGuard(root: RefObject<HTMLElement | null>, dirty: boolean, busy: boolean, discard: () => void) {
  const latest = useRef(discard);
  latest.current = discard;
  const owner = useRef<HTMLElement | null>(null);
  useEffect(() => {
    owner.current = root.current ?? owner.current;
    if (owner.current) setNfoDraft({owner:owner.current,dirty,busy,discard:()=>latest.current()});
  },[root,dirty,busy]);
  useEffect(() => {
    const element=root.current;
    return () => { queueMicrotask(()=>{if(!element?.isConnected)clearNfoDraft(element);}); };
  },[root]);
}