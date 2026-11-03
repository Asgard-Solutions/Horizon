"""Generate a small synthetic test library with FFmpeg (test patterns + sine tone; no copyrighted content).

Usage:  python scripts/make_sample_media.py D:\\TestMedia
Requires ffmpeg on PATH. Creates movies, TV episodes, an AVI (unsupported in browsers), NFOs and posters.
Existing files are never overwritten.
"""
import shutil
import subprocess
import sys
from pathlib import Path

SRC = ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=24", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100"]
H264 = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-c:a", "aac", "-movflags", "+faststart"]
FILES = [
    ("Movies/Sample Movie (2024).mp4", 90, H264),
    ("Movies/Big Test Pattern (2021)/Big.Test.Pattern.2021.1080p.BluRay.m4v", 60, H264),
    ("Movies/Legacy Clip (1999).avi", 20, ["-c:v", "mpeg4", "-c:a", "mp3"]),
    ("TV/Sample Show/Season 01/Sample Show - S01E01.mkv", 45, H264[:-2]),
    ("TV/Sample Show/Season 01/Sample Show - S01E02.mp4", 45, H264),
    ("TV/Other Series (2019)/Season 2/Other.Series.S02E05.720p.mp4", 30, H264),
]
POSTERS = [("Movies/Big Test Pattern (2021)/poster.jpg", "0x1f3a5f"), ("TV/Sample Show/poster.jpg", "0x5f1f3a")]
TEXT = {
    "TV/Sample Show/tvshow.nfo": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<tvshow><title>Sample Show</title><year>2023</year>"
                                 "<plot>A synthetic test series generated with FFmpeg test patterns.</plot></tvshow>\n",
    "Movies/Sample Movie (2024).nfo": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<movie><title>Sample Movie</title><year>2024</year>"
                                      "<plot>A 90-second synthetic H.264/AAC test pattern used to verify playback, seeking and resume.</plot></movie>\n",
    "Movies/readme.txt": "not a video - must be ignored by the scanner\n",
}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found on PATH")
    root = Path(sys.argv[1])
    for rel, seconds, codec in FILES:
        out = root / rel
        if out.exists():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-n", *SRC, "-t", str(seconds), *codec, str(out)], check=True)
    for rel, color in POSTERS:
        out = root / rel
        if not out.exists():
            subprocess.run(["ffmpeg", "-loglevel", "error", "-n", "-f", "lavfi", "-i", f"color=c={color}:s=600x900",
                            "-frames:v", "1", str(out)], check=True)
    for rel, text in TEXT.items():
        out = root / rel
        if not out.exists():
            out.write_text(text, encoding="utf-8")
    print(f"Sample library ready in {root}")


if __name__ == "__main__":
    main()
