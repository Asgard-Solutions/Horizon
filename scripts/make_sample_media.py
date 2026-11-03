"""Generate a small synthetic test library with FFmpeg (test patterns + sine tone; no copyrighted content).

Usage:  python scripts/make_sample_media.py D:\\TestMedia [--demo-series D:\\TestDemoSeries]
Requires ffmpeg on PATH. Creates movies, TV episodes, an AVI (unsupported in browsers), NFOs and posters.
--demo-series additionally writes the Horizon demo series ("Northern Survey", 2 seasons with artwork) into its OWN
folder, so it can be added as a separate test-only library and removed without touching anything else.
This is a development/testing tool only: the app never runs it and never adds demo titles to a library by itself.
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
# Abstract gradient artwork so detail pages have real local art to show.
GRADIENTS = [("Movies/Sample Movie (2024)-fanart.jpg", "1920x1080", "0x0a0e15:0x1f5f55:0x2c3f63")]
TEXT = {
    "TV/Sample Show/tvshow.nfo": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<tvshow><title>Sample Show</title><year>2023</year>"
                                 "<plot>A synthetic test series generated with FFmpeg test patterns.</plot></tvshow>\n",
    "Movies/Sample Movie (2024).nfo": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<movie><title>Sample Movie</title><year>2024</year>"
                                      "<plot>A 90-second synthetic H.264/AAC test pattern used to verify playback, seeking and resume.</plot></movie>\n",
    "Movies/readme.txt": "not a video - must be ignored by the scanner\n",
}

# Horizon demo series (test-only, separate folder; see --demo-series).
NS = "TV/Northern Survey (2022)"
DEMO_FILES = [
    (f"{NS}/Season 01/Northern Survey - S01E01 - Arrival.mp4", 40, H264),
    (f"{NS}/Season 01/Northern Survey - S01E02 - The Long Night.mp4", 40, H264),
    (f"{NS}/Season 01/Northern Survey - S01E03 - Signals.mp4", 40, H264),
    (f"{NS}/Season 02/Northern Survey - S02E01 - Thaw.mp4", 35, H264),
    (f"{NS}/Season 02/Northern Survey - S02E02 - Return.mp4", 35, H264),
]
DEMO_GRADIENTS = [
    (f"{NS}/fanart.jpg", "1920x1080", "0x101925:0x22506a:0x8a6a3c"),
    (f"{NS}/poster.jpg", "600x900", "0x0d2a33:0x3a7f78:0xe7b778"),
    (f"{NS}/Season 01/Northern Survey - S01E01 - Arrival-thumb.jpg", "640x360", "0x14324a:0x55d9be"),
    (f"{NS}/Season 01/Northern Survey - S01E02 - The Long Night-thumb.jpg", "640x360", "0x0a0e15:0x2c3f63"),
    (f"{NS}/Season 02/Northern Survey - S02E01 - Thaw-thumb.jpg", "640x360", "0x3a2a14:0xe7b778"),
]
DEMO_TEXT = {
    f"{NS}/tvshow.nfo": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<tvshow><title>Northern Survey</title><year>2022</year>"
                        "<plot>A synthetic two-season test series: survey crews, long nights and test-pattern skies.</plot></tvshow>\n",
}
EPISODE_PLOTS = {
    "Season 01/Northern Survey - S01E01 - Arrival": "The crew reaches the station as the last light fades.",
    "Season 01/Northern Survey - S01E02 - The Long Night": "Weeks without sunrise test the team and the equipment.",
    "Season 01/Northern Survey - S01E03 - Signals": "A repeating pattern appears on every receiver at once.",
    "Season 02/Northern Survey - S02E01 - Thaw": "Spring arrives early and the ice begins to move.",
    "Season 02/Northern Survey - S02E02 - Return": "The survey ends where it began.",
}
for _stem, _plot in EPISODE_PLOTS.items():
    DEMO_TEXT[f"{NS}/{_stem}.nfo"] = (f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<episodedetails><title>{_stem.split(' - ')[-1]}</title>"
                                 f"<plot>{_plot}</plot></episodedetails>\n")


def build(root: Path, files, posters, gradients, text) -> None:
    for rel, seconds, codec in files:
        out = root / rel
        if out.exists():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-n", *SRC, "-t", str(seconds), *codec, str(out)], check=True)
    for rel, color in posters:
        out = root / rel
        if not out.exists():
            subprocess.run(["ffmpeg", "-loglevel", "error", "-n", "-f", "lavfi", "-i", f"color=c={color}:s=600x900",
                            "-frames:v", "1", str(out)], check=True)
    for rel, size, colors in gradients:
        out = root / rel
        if not out.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            c = colors.split(":")
            args = ":".join(f"c{i}={v}" for i, v in enumerate(c))
            subprocess.run(["ffmpeg", "-loglevel", "error", "-n", "-f", "lavfi", "-i", f"gradients=s={size}:{args}:n={len(c)}:seed=7",
                            "-frames:v", "1", str(out)], check=True)
    for rel, body in text.items():
        out = root / rel
        if not out.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(body, encoding="utf-8")


def main():
    args = sys.argv[1:]
    demo = None
    if "--demo-series" in args:
        i = args.index("--demo-series")
        if i + 1 >= len(args):
            sys.exit(__doc__)
        demo = Path(args[i + 1])
        del args[i:i + 2]
    if len(args) != 1:
        sys.exit(__doc__)
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found on PATH")
    root = Path(args[0])
    if demo and (demo.resolve() == root.resolve() or root.resolve() in demo.resolve().parents):
        sys.exit("--demo-series must be a separate folder outside the sample library")
    build(root, FILES, POSTERS, GRADIENTS, TEXT)
    print(f"Sample library ready in {root}")
    if demo:
        build(demo, DEMO_FILES, [], DEMO_GRADIENTS, DEMO_TEXT)
        print(f"Demo series (test only) ready in {demo} - add it as its own library, remove it when done")


if __name__ == "__main__":
    main()
