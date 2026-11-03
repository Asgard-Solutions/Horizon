"""Filename / folder parsing for movies and TV episodes. Pure functions, no I/O."""
import re

VIDEO_EXTENSIONS = {
    ".mp4", ".m4v", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv",
    ".mpg", ".mpeg", ".ts", ".m2ts", ".mts", ".vob", ".divx", ".ogv", ".3gp",
}
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

_RELEASE_TAG = re.compile(
    r"(?i)(?<![a-z0-9])(480p|576p|720p|1080[pi]|2160p|4k|uhd|x26[45]|h\.?26[45]|hevc|avc|xvid|divx|"
    r"web[- ]?dl|webrip|web|bluray|blu[- ]?ray|brrip|bdrip|dvdrip|dvd|hdtv|hdrip|remux|proper|repack|"
    r"aac|ac3|eac3|dts|ddp?5\.1|atmos|hdr10?|dv|10bit|8bit|extended|unrated|remastered)(?![a-z0-9])"
)
_EPISODE_SXXEXX = re.compile(r"(?i)(?<![a-z0-9])s(\d{1,3})[ ._-]?e(\d{1,4})(?:(?:-?e|-)(\d{1,4}))?(?!\d)")
_EPISODE_NXNN = re.compile(r"(?<![\dx])(\d{1,2})x(\d{2,3})(?![\dp])", re.I)
_SEASON_DIR = re.compile(r"(?i)^(?:season|series|staffel|saison|temporada)[ ._-]*(\d{1,3})$|^s(\d{1,3})$")
_YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
_TRAILING_YEAR = re.compile(r"^(.*?)[\s._\-]*[(\[]?((?:19|20)\d{2})[)\]]?$")


def is_video(filename: str) -> bool:
    dot = filename.rfind(".")
    return dot > 0 and filename[dot:].lower() in VIDEO_EXTENSIONS


def split_ext(filename: str) -> tuple[str, str]:
    dot = filename.rfind(".")
    if dot <= 0:
        return filename, ""
    return filename[:dot], filename[dot + 1:].lower()


def clean_name(text: str) -> str:
    text = re.sub(r"[._]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -[](){}")


def sort_key(title: str) -> str:
    t = title.lower()
    for article in ("the ", "a ", "an "):
        if t.startswith(article):
            t = t[len(article):]
            break
    return t


def _strip_release_tags(text: str) -> str:
    m = _RELEASE_TAG.search(text)
    if m:
        text = text[: m.start()]
    return clean_name(text)


def split_title_year(name: str) -> tuple[str, int | None]:
    """'Other Series (2019)' -> ('Other Series', 2019)."""
    cleaned = clean_name(name)
    m = _TRAILING_YEAR.match(cleaned)
    if m and m.group(1).strip(" -([."):
        return clean_name(m.group(1)), int(m.group(2))
    return cleaned, None


def season_from_dir(dirname: str) -> int | None:
    m = _SEASON_DIR.match(dirname.strip())
    if not m:
        return None
    return int(m.group(1) or m.group(2))


def parse_episode(filename: str, rel_dirs: list[str]) -> dict | None:
    """Return episode info or None if the filename does not look like a TV episode.

    rel_dirs: directory names between the library root (exclusive) and the file (inclusive of parent).
    """
    stem, _ = split_ext(filename)
    m = _EPISODE_SXXEXX.search(stem) or _EPISODE_NXNN.search(stem)
    if not m:
        return None
    season, episode = int(m.group(1)), int(m.group(2))
    episode_end = None
    if m.re is _EPISODE_SXXEXX and m.group(3):
        end = int(m.group(3))
        if episode < end <= episode + 10:
            episode_end = end

    file_show = clean_name(stem[: m.start()])
    parent = rel_dirs[-1] if rel_dirs else None
    show_folder = None
    if parent is not None and season_from_dir(parent) is not None:
        show_folder = rel_dirs[-2] if len(rel_dirs) >= 2 else None
    elif parent is not None:
        show_folder = parent

    if show_folder and (season_from_dir(parent) is not None or not file_show):
        show_name = show_folder
    else:
        show_name = file_show or show_folder
    if not show_name:
        return None
    title, year = split_title_year(show_name)

    ep_title = _strip_release_tags(stem[m.end():]) or None
    return {
        "show_title": title,
        "show_year": year,
        "show_key": f"{title.lower()}|{year or ''}",
        "season": season,
        "episode": episode,
        "episode_end": episode_end,
        "episode_title": ep_title,
        "uses_show_folder": bool(show_folder) and show_name == show_folder,
    }


def parse_movie(filename: str, rel_dirs: list[str]) -> dict:
    stem, _ = split_ext(filename)
    title, year = _title_year_from_text(stem)
    parent = rel_dirs[-1] if rel_dirs else None
    if parent and (year is None or not title):
        p_title, p_year = _title_year_from_text(parent)
        if p_year is not None or not title:
            title, year = p_title or title, p_year or year
    return {"title": title or clean_name(stem), "year": year}


def _title_year_from_text(text: str) -> tuple[str, int | None]:
    cleaned = clean_name(text)
    years = [m for m in _YEAR.finditer(cleaned) if m.start() > 0]
    if years:
        m = years[-1]
        return clean_name(cleaned[: m.start()]), int(m.group(1))
    return _strip_release_tags(cleaned), None
