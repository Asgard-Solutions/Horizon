import { Navigate, useParams } from "react-router-dom";
import { HomeScreen } from "../home/HomeScreen";
import { parseMediaType } from "../home/context";

export default function Home() {
  const { mediaType } = useParams();
  const type = parseMediaType(mediaType ?? null);
  if (mediaType && !type) return <Navigate to="/" replace />;
  return <HomeScreen key={type ?? "selection"} type={type} />;
}
