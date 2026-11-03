/** Horizon mark: an interrupted orbit with a horizontal stroke. Original vector, works at 24 px and splash size. */
export function HorizonMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true" className="h-mark">
      <path d="M6.2 21.5A11 11 0 1 1 25.8 21.5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M2.5 21.5h7.5M14 21.5h15.5" stroke="var(--h-color-accent-aurora)" strokeWidth="2.2" strokeLinecap="round" />
      <circle cx="16" cy="13.5" r="2.4" fill="var(--h-color-accent-amber)" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="h-wordmark" data-testid="brand">
      <HorizonMark />
      <span>HORIZON</span>
    </span>
  );
}
