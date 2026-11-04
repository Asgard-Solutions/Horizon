/** The REELHEIM Line: a 2 px line that bends toward the focused Filmstrip card only. Pure SVG, no animation loop. */
export function HorizonLine({ anchor, width }: { anchor: number | null; width: number }) {
  if (!width) return null;
  const y = 6;
  const dip = 16;
  const x = anchor ?? width * 0.18;
  const d = anchor === null
    ? `M 0 ${y} L ${width} ${y}`
    : `M 0 ${y} L ${x - 170} ${y} C ${x - 70} ${y}, ${x - 50} ${y + dip}, ${x} ${y + dip} C ${x + 50} ${y + dip}, ${x + 70} ${y}, ${x + 170} ${y} L ${width} ${y}`;
  return (
    <svg className="horizon-line" width="100%" height="26" viewBox={`0 0 ${width} 26`} preserveAspectRatio="none" aria-hidden="true"
      data-testid="horizon-line">
      <defs>
        <linearGradient id="hl-grad" gradientUnits="userSpaceOnUse" x1="0" x2={width} y1="0" y2="0">
          <stop offset="0" stopColor="var(--h-color-border-default)" stopOpacity="0.5" />
          <stop offset={Math.max(0, (x - 260) / width)} stopColor="var(--h-color-border-default)" stopOpacity="0.6" />
          <stop offset={Math.max(0, (x - 120) / width)} stopColor="var(--h-color-accent-amber)" stopOpacity="0.55" />
          <stop offset={Math.min(1, x / width)} stopColor="var(--h-color-accent-aurora)" />
          <stop offset={Math.min(1, (x + 180) / width)} stopColor="var(--h-color-border-default)" stopOpacity="0.6" />
          <stop offset="1" stopColor="var(--h-color-border-default)" stopOpacity="0.3" />
        </linearGradient>
      </defs>
      <path d={d} stroke="url(#hl-grad)" strokeWidth="2" fill="none" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
