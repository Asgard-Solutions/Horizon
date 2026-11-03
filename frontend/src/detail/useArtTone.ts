import { useEffect, useState } from "react";

/** Mean luminance (0..1) of the artwork's text side, so the scrim can deepen over bright art. */
export function useArtTone(url: string | undefined): number {
  const [tone, setTone] = useState(0);
  useEffect(() => {
    if (!url) return void setTone(0);
    let live = true;
    const img = new Image();
    img.onload = () => {
      const c = document.createElement("canvas");
      c.width = 32;
      c.height = 18;
      const g = c.getContext("2d");
      if (!g || !live) return;
      g.drawImage(img, 0, 0, 32, 18);
      try {
        const d = g.getImageData(0, 0, 20, 18).data;
        let sum = 0;
        for (let i = 0; i < d.length; i += 4) sum += 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
        setTone(sum / (d.length / 4) / 255);
      } catch {
        setTone(0.5);
      }
    };
    img.src = url;
    return () => { live = false; };
  }, [url]);
  return tone;
}
