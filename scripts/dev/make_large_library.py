"""TEST ONLY: build a large synthetic library from one small clip (hard links, so it costs almost no disk).

Usage: python scripts/dev/make_large_library.py <empty folder> --source <clip.mp4> [--movies 3000] [--shows 150]
Creates movies with and without NFO files (genres, some <set> collections), folder-based collections, a few posters,
and TV shows with seasons. Titles are clearly synthetic ("Test Title 0001"). The app never runs this by itself.
"""
import argparse
import os
import shutil
from pathlib import Path

GENRES = ["Drama", "Comedy", "Science Fiction", "Documentary", "Thriller", "Animation", "Adventure", "Romance",
          "Horror", "Family", "Mystery", "Fantasy", "Crime", "History", "Music", "War", "Western", "Sport"]


def link(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def nfo(kind: str, title: str, year: int, genres: list[str], collection: str | None = None) -> str:
    g = "".join(f"<genre>{x}</genre>" for x in genres)
    s = f"<set><name>{collection}</name></set>" if collection else ""
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<{kind}><title>{title}</title><year>{year}</year>{g}{s}</{kind}>\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--source", required=True)
    ap.add_argument("--poster")
    ap.add_argument("--movies", type=int, default=3000)
    ap.add_argument("--shows", type=int, default=150)
    a = ap.parse_args()
    root, src = Path(a.root), Path(a.source)
    for n in range(1, a.movies + 1):
        title, year = f"Test Title {n:04d}", 1950 + n % 75
        if n % 10 in (1, 2, 3):  # folder collection of 3: "Saga 012/Test Title 0121 (1996)/..."
            d = root / "Movies" / f"Saga {n // 10:03d}" / f"{title} ({year})"
        else:
            d = root / "Movies" / f"{title} ({year})"
        link(src, d / f"{title} ({year}).mp4")
        if n % 10 < 7:  # 70% have an NFO; a fifth of those name an explicit set
            genres = [GENRES[n % len(GENRES)]] + ([GENRES[(n * 7) % len(GENRES)]] if n % 3 == 0 else [])
            col = f"Test Set {n % 40:02d}" if n % 5 == 0 else None
            (d / f"{title} ({year}).nfo").write_text(nfo("movie", title, year, genres, col), encoding="utf-8")
        if a.poster and n % 4 == 0:
            link(Path(a.poster), d / "poster.jpg")
    for n in range(1, a.shows + 1):
        show = root / "TV" / f"Test Series {n:03d}"
        if n % 2:
            (show / "tvshow.nfo").parent.mkdir(parents=True, exist_ok=True)
            (show / "tvshow.nfo").write_text(nfo("tvshow", f"Test Series {n:03d}", 2000 + n % 25, [GENRES[n % len(GENRES)]]), encoding="utf-8")
        for s in (1, 2):
            for e in (1, 2, 3):
                link(src, show / f"Season {s:02d}" / f"Test Series {n:03d} - S{s:02d}E{e:02d}.mp4")
    print(f"Large test library ready in {root}")


if __name__ == "__main__":
    main()
