import { FolderPlus, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { HorizonMark } from "../components/HorizonMark";

/** First run (no folders) or folders with no supported media. Abstract horizon artwork only — no fake titles. */
export function FirstRun({ hasFolders }: { hasFolders: boolean }) {
  const { auth } = useAuth();
  const navigate = useNavigate();
  const host = auth.role === "host";
  return (
    <section className="firstrun" data-testid="first-run">
      <svg className="firstrun-art" viewBox="0 0 1600 600" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
        <defs>
          <radialGradient id="fr-glow" cx="50%" cy="100%" r="60%">
            <stop offset="0" stopColor="#87E8D0" stopOpacity="0.16" />
            <stop offset="1" stopColor="#0A0E15" stopOpacity="0" />
          </radialGradient>
        </defs>
        <rect width="1600" height="600" fill="url(#fr-glow)" />
        <path d="M-50 560 Q800 250 1650 560" stroke="#87E8D0" strokeOpacity="0.6" strokeWidth="2" fill="none" />
        <path d="M-50 585 Q800 330 1650 585" stroke="#E7B778" strokeOpacity="0.28" strokeWidth="1.2" fill="none" />
        <path d="M-50 600 Q800 400 1650 600" stroke="#344656" strokeWidth="1" fill="none" />
      </svg>
      <div className="firstrun-copy">
        <HorizonMark size={56} />
        <h1 data-testid="first-run-title">{hasFolders ? "No supported media found yet" : "Your cinema starts with a folder"}</h1>
        <p>
          {hasFolders
            ? "Your library folders were scanned, but no movies or episodes were recognised. Check the folder contents or scan again."
            : "Point Horizon at a folder on this PC, a mapped drive or a network share like \\\\NAS\\Media. Files are only read, never changed."}
        </p>
        {host ? (
          <button className="hbtn hbtn--primary hbtn--large" data-autofocus onClick={() => navigate("/settings")}
            data-testid="home-add-folder-button">
            {hasFolders ? <RefreshCw size={24} /> : <FolderPlus size={24} />}
            {hasFolders ? "Review folders and scan again" : "Add media folder"}
          </button>
        ) : (
          <p className="firstrun-note" data-testid="first-run-device-note">
            Media folders are added on the host PC. Once it has scanned a folder, your titles will appear here.
          </p>
        )}
      </div>
    </section>
  );
}
