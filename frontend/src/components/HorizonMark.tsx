import emblem from "../assets/reelheim-emblem-icon-256.png";

/** Supplied REELHEIM emblem; keep the existing export for internal callers. */
export function HorizonMark({ size = 28 }: { size?: number }) {
  return <img src={emblem} width={size} height={size} alt="" aria-hidden="true" className="h-mark" />;
}

export function Wordmark() {
  return (
    <span className="h-wordmark" data-testid="brand">
      <HorizonMark />
      <span>REELHEIM</span>
    </span>
  );
}
