import { Link } from "react-router-dom";
import { useAuth } from "../App";
import { scopedPath } from "../home/context";

export function NfoEditLink({ kind, id, label = "Edit NFO" }: { kind: "movie"|"tv"|"episode"; id:number; label?:string }) {
  const { auth } = useAuth();
  if (auth.role !== "host") return null;
  return <Link className="hbtn hbtn--quiet" to={scopedPath(`/settings?section=libraries&nfo_kind=${kind}&nfo_id=${id}`,kind==="movie"?"movie":"tv")}>{label}</Link>;
}
