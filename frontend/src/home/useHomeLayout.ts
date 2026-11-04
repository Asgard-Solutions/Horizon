import { useEffect, useState } from "react";
import { getScalePref } from "../theme/uiScale";

function currentLayout() {
  const zoom = Number(document.documentElement.dataset.uiScale) || 1;
  const width = window.innerWidth / zoom;
  const height = window.innerHeight / zoom;
  return {
    compact: (getScalePref() !== "auto" && zoom > 1) || width < 1100 || height < 600 || width / height <= 4 / 3,
    stackedHome: width < 640,
    stackedHub: width < 720,
  };
}

export function useHomeLayout() {
  const [layout, setLayout] = useState(currentLayout);
  useEffect(() => {
    const refresh = () => setLayout(currentLayout());
    window.addEventListener("resize", refresh);
    window.addEventListener("horizon-ui-scale", refresh);
    return () => { window.removeEventListener("resize", refresh); window.removeEventListener("horizon-ui-scale", refresh); };
  }, []);
  return layout;
}
