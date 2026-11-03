import { CheckCircle2 } from "lucide-react";
import { formatTime, isPartial, progressRatio, remainingLabel } from "../format";
import type { Progress } from "../types";

/** Real watch state only: a Watched mark, or a progress bar with elapsed and remaining time. */
export function WatchProgress({ progress, testId }: { progress: Progress | null; testId: string }) {
  if (progress?.watched) {
    return <p className="dt-watched" data-testid={`${testId}-watched`}><CheckCircle2 size={20} /> Watched</p>;
  }
  if (!isPartial(progress)) return null;
  const ratio = progressRatio(progress);
  return (
    <div className="dt-progress" data-testid={testId}>
      <div className="dt-progress-bar" role="progressbar" aria-label="Watched so far" aria-valuemin={0} aria-valuemax={100}
        aria-valuenow={Math.round(ratio * 100)}><span style={{ width: `${ratio * 100}%` }} /></div>
      <span className="dt-progress-text">
        {formatTime(progress!.position)}{progress!.duration ? ` of ${formatTime(progress!.duration)}` : ""}
        {remainingLabel(progress!) && <b> · {remainingLabel(progress!)}</b>}
      </span>
    </div>
  );
}
