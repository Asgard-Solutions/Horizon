import { useEffect } from "react";
import { useBack } from "../hooks";
import { focusFirst } from "../nav/spatial";

interface Props {
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Controller-friendly replacement for window.confirm(). */
export function ConfirmDialog({ title, message, confirmLabel, onConfirm, onCancel }: Props) {
  useBack(() => onCancel());
  useEffect(() => {
    const t = window.setTimeout(() => focusFirst(document.querySelector(".modal")), 20);
    return () => window.clearTimeout(t);
  }, []);
  return (
    <div className="modal-backdrop" data-nav-scope="modal" data-testid="confirm-dialog">
      <div className="modal modal--small" role="alertdialog" aria-label={title}>
        <h2>{title}</h2>
        <p className="muted">{message}</p>
        <div className="detail-actions">
          <button className="btn" data-autofocus onClick={onCancel} data-testid="confirm-dialog-cancel-button">Cancel</button>
          <button className="btn btn--danger" onClick={onConfirm} data-testid="confirm-dialog-confirm-button">{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
