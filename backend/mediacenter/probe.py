"""Optional media inspection with FFprobe (external executable, invoked as a separate process; never bundled here)."""
import json
import os
import shutil
import subprocess
from pathlib import Path

from .config import PROJECT_DIR

BROWSER_SAFE_CONTAINERS = {"mp4", "m4v", "mov", "webm"}
BROWSER_UNSUPPORTED_CONTAINERS = {"avi", "wmv", "flv", "mpg", "mpeg", "ts", "m2ts", "mts", "vob", "divx", "3gp"}
SAFE_VIDEO = {"h264", "vp8", "vp9", "av1"}
MAYBE_VIDEO = {"hevc"}
SAFE_AUDIO = {"aac", "mp3", "opus", "vorbis", "flac"}
MAYBE_AUDIO = {"ac3", "eac3"}
MIME = {"mp4": "video/mp4", "m4v": "video/mp4", "mov": "video/mp4", "webm": "video/webm",
        "mkv": "video/x-matroska", "ogv": "video/ogg", "avi": "video/x-msvideo", "wmv": "video/x-ms-wmv",
        "flv": "video/x-flv", "ts": "video/mp2t", "m2ts": "video/mp2t", "mts": "video/mp2t",
        "mpg": "video/mpeg", "mpeg": "video/mpeg", "vob": "video/mpeg", "3gp": "video/3gpp", "divx": "video/x-msvideo"}


def find_ffprobe(configured: str | None) -> str | None:
    if configured and Path(configured).is_file():
        return configured
    bundled = PROJECT_DIR / "tools" / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
    if bundled.is_file():
        return str(bundled)
    return shutil.which("ffprobe")


def ffprobe_version(ffprobe: str | None) -> str | None:
    if not ffprobe:
        return None
    try:
        out = subprocess.run([ffprobe, "-version"], capture_output=True, text=True, timeout=10)
        return out.stdout.splitlines()[0] if out.stdout else None
    except (OSError, subprocess.SubprocessError):
        return None


def probe_file(ffprobe: str, path: str) -> dict:
    cmd = [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        return {"error": (out.stderr or "ffprobe failed").strip()[:500]}
    data = json.loads(out.stdout or "{}")
    fmt = data.get("format", {})
    video, audio, subs = [], [], []
    for s in data.get("streams", []):
        t = s.get("codec_type")
        if t == "video" and not s.get("disposition", {}).get("attached_pic"):
            video.append({"codec": s.get("codec_name"), "profile": s.get("profile"), "width": s.get("width"),
                          "height": s.get("height"), "pix_fmt": s.get("pix_fmt"), "level": s.get("level")})
        elif t == "audio":
            audio.append({"codec": s.get("codec_name"), "channels": s.get("channels"),
                          "language": s.get("tags", {}).get("language")})
        elif t == "subtitle":
            subs.append({"codec": s.get("codec_name"), "language": s.get("tags", {}).get("language")})
    duration = fmt.get("duration")
    return {"format_name": fmt.get("format_name"), "duration": float(duration) if duration else None,
            "bit_rate": fmt.get("bit_rate"), "video": video, "audio": audio, "subtitles": subs}


def _codec_string(video: dict | None, audio: dict | None) -> str | None:
    parts = []
    if video:
        c = video.get("codec")
        if c == "h264":
            profile = {"Baseline": "42E0", "Constrained Baseline": "42E0", "Main": "4D40", "High": "6400"}.get(
                video.get("profile") or "", "6400")
            level = video.get("level") or 40
            parts.append(f"avc1.{profile}{int(level):02X}")
        elif c == "hevc":
            parts.append("hvc1.1.6.L93.B0")
        elif c == "vp9":
            parts.append("vp09.00.10.08")
        elif c == "vp8":
            parts.append("vp8")
        elif c == "av1":
            parts.append("av01.0.05M.08")
    if audio:
        a = audio.get("codec")
        parts.append({"aac": "mp4a.40.2", "mp3": "mp4a.6B", "opus": "opus", "vorbis": "vorbis", "flac": "flac",
                      "ac3": "ac-3", "eac3": "ec-3"}.get(a, a or ""))
    parts = [p for p in parts if p]
    return ", ".join(parts) if parts else None


def assess_playback(container: str, probe: dict | None) -> dict:
    """Best-effort server-side verdict. The client still confirms with canPlayType() and real media events."""
    reasons: list[str] = []
    mime = MIME.get(container, "application/octet-stream")
    name = container.upper()

    if container in BROWSER_UNSUPPORTED_CONTAINERS:
        reasons.append(f"The {name} container is not supported by web browsers. "
                       "Phase 0 does not transcode, so this file needs a native player or a future transcoding feature.")
        return {"status": "unsupported", "reasons": reasons, "mime": mime, "codecs": None}

    status = "supported" if container in BROWSER_SAFE_CONTAINERS else "maybe"
    if container == "mkv":
        reasons.append("MKV support depends on the browser: Chromium/Edge usually play MKV with H.264/AAC, "
                       "other browsers may refuse it.")
    elif container not in BROWSER_SAFE_CONTAINERS:
        reasons.append(f"{name} files are rarely playable in browsers.")

    if not probe or probe.get("error"):
        reasons.append("Codecs were not inspected (FFprobe not available or failed), so compatibility is a guess.")
        return {"status": "unknown" if status == "supported" else status, "reasons": reasons, "mime": mime, "codecs": None}

    video = probe["video"][0] if probe.get("video") else None
    audio = probe["audio"][0] if probe.get("audio") else None
    if video:
        vc = video.get("codec")
        if vc in MAYBE_VIDEO:
            status = "maybe" if status != "unsupported" else status
            reasons.append("HEVC/H.265 video only plays where the device has hardware/extension support.")
        elif vc not in SAFE_VIDEO:
            status = "unsupported"
            reasons.append(f"Video codec '{vc}' is not supported by web browsers.")
        if vc == "h264" and (video.get("pix_fmt") or "").endswith("10le"):
            status = "unsupported"
            reasons.append("10-bit H.264 (Hi10P) is not decodable by browsers.")
    else:
        reasons.append("No video stream was found.")
    if audio:
        ac = audio.get("codec")
        if ac in MAYBE_AUDIO:
            if status == "supported":
                status = "maybe"
            reasons.append(f"Audio codec '{ac}' (Dolby) only plays on some platforms; video may play without sound.")
        elif ac not in SAFE_AUDIO:
            if status == "supported":
                status = "maybe"
            reasons.append(f"Audio codec '{ac}' is not supported by browsers; video may play without sound.")
    return {"status": status, "reasons": reasons, "mime": mime, "codecs": _codec_string(video, audio)}
