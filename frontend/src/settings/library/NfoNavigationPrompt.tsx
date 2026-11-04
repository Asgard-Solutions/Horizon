import { useEffect, useSyncExternalStore } from "react";
import { useBlocker, useLocation } from "react-router-dom";
import { ConfirmDialog } from "../../components/ConfirmDialog";

type Draft = {owner:HTMLElement;dirty:boolean;busy:boolean;discard:()=>void};
let draft:Draft|null=null;
const listeners=new Set<()=>void>();
const subscribe=(notify:()=>void)=>{listeners.add(notify);return()=>{listeners.delete(notify);};};
const snapshot=()=>draft;
export function setNfoDraft(value:Draft){draft=value;listeners.forEach(notify=>notify());}
export function clearNfoDraft(owner:HTMLElement|null){if(draft?.owner===owner){draft=null;listeners.forEach(notify=>notify());}}

/** Kept outside Settings Activity; React Router handles browser Back/Forward and in-app links. */
export function NfoNavigationPrompt(){
  const current=useSyncExternalStore(subscribe,snapshot,()=>null);
  const location=useLocation();
  const blocker=useBlocker(({currentLocation,nextLocation})=>!!(current?.dirty||current?.busy)&&currentLocation.pathname!==nextLocation.pathname);
  useEffect(()=>{
    if(current&&!current.owner.isConnected)clearNfoDraft(current.owner);
  },[current,location.key]);
  useEffect(()=>{
    if(blocker.state==="blocked"&&(!current||(!current.dirty&&!current.busy)))blocker.proceed();
  },[blocker,current]);
  useEffect(()=>{
    const before=(event:BeforeUnloadEvent)=>{if(current?.dirty||current?.busy){event.preventDefault();event.returnValue="";}};
    window.addEventListener("beforeunload",before);
    return()=>window.removeEventListener("beforeunload",before);
  },[current]);
  if(blocker.state!=="blocked")return null;
  if(current?.busy)return <ConfirmDialog title="NFO update in progress" message="Wait for the NFO operation to finish before leaving." confirmLabel="Stay on page" onCancel={()=>blocker.reset()} onConfirm={()=>blocker.reset()}/>;
  return <ConfirmDialog title="Discard unsaved NFO changes?" message="Your changes have not been saved to the NFO file. Discard them to leave this page."
    confirmLabel="Discard changes & leave" onCancel={()=>blocker.reset()} onConfirm={()=>{if(current){clearNfoDraft(current.owner);current.discard();}blocker.proceed();}}/>;
}