"""Read-only, file-scoped sidecars; deliberately independent of probing and scanning.

Only ordinary sibling SRT/VTT files are offered. Conversion keeps text and b/i/u,
discarding VTT identifiers, positioning, STYLE/REGION/NOTE blocks and other markup.
"""
import codecs
import hashlib
import html
import os
import re
import stat
from html.parser import HTMLParser

from fastapi import HTTPException

from . import paths

MAX_SUBTITLE_BYTES = 2 * 1024 * 1024
MAX_CUES = 10_000
MAX_TRACKS = 64
MAX_DIRECTORY_ENTRIES = 10_000

# ISO 639-1 codes and common ISO 639-2 terminology/bibliographic aliases.
LANGUAGES = set("""aa ab ae af ak am an ar as av ay az ba be bg bh bi bm bn bo br bs ca ce ch co cr cs cu cv cy
da de dv dz ee el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi ho hr ht hu hy hz ia id ie ig
ii ik io is it iu ja jv ka kg ki kj kk kl km kn ko kr ks ku kv kw ky la lb lg li ln lo lt lu lv mg mh mi mk ml
mn mr ms mt my na nb nd ne ng nl nn no nr nv ny oc oj om or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se
sg si sk sl sm sn so sq sr ss st su sv sw ta te tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve vi vo wa wo
xh yi yo za zh zu""".split())
LANGUAGE_ALIASES = dict(pair.split(":") for pair in """
afr:af alb:sq sqi:sq amh:am ara:ar arm:hy hye:hy asm:as aze:az baq:eu eus:eu bel:be ben:bn bos:bs
bre:br bul:bg bur:my mya:my cat:ca chi:zh zho:zh cze:cs ces:cs cym:cy wel:cy dan:da dut:nl nld:nl
ell:el gre:el eng:en epo:eo est:et fao:fo fas:fa per:fa fin:fi fra:fr fre:fr fry:fy geo:ka kat:ka
ger:de deu:de gla:gd gle:ga glg:gl guj:gu hat:ht hau:ha heb:he hin:hi hrv:hr hun:hu ice:is isl:is
ibo:ig ind:id ita:it jav:jv jpn:ja kan:kn kaz:kk khm:km kir:ky kor:ko kur:ku lao:lo lat:la lav:lv
lit:lt ltz:lb mac:mk mkd:mk mal:ml mao:mi mri:mi mar:mr may:ms msa:ms mlt:mt mon:mn nep:ne nor:no
nob:nb nno:nn oci:oc ori:or pan:pa pol:pl por:pt pus:ps que:qu roh:rm ron:ro rum:ro rus:ru san:sa
sin:si slk:sk slo:sk slv:sl som:so spa:es srp:sr swa:sw swe:sv tam:ta tel:te tgk:tg tha:th tib:bo
bod:bo tuk:tk tur:tr uig:ug ukr:uk urd:ur uzb:uz vie:vi yid:yi yor:yo zul:zu
""".split())
TAG = re.compile(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*\Z")
TRACK_ID = re.compile(r"[0-9a-f]{64}\Z")
SRT_TIME = r"[0-9]{2,6}:[0-5][0-9]:[0-5][0-9],[0-9]{3}"
VTT_TIME = r"(?:[0-9]{2,6}:)?[0-5][0-9]:[0-5][0-9]\.[0-9]{3}"
SRT_TIMING = re.compile(rf"({SRT_TIME})[ \t]+-->[ \t]+({SRT_TIME})\Z")
VTT_TIMING = re.compile(rf"({VTT_TIME})[ \t]+-->[ \t]+({VTT_TIME})(?:[ \t]+([^\n]*))?\Z")


def _key(path):
    return os.path.normcase(os.path.realpath(path))


def _folder_error():
    return HTTPException(503, "Subtitle folder is unavailable or too large. Check the source connection and permissions, then retry.")


def _invalid(reason):
    return HTTPException(422, f"Invalid subtitle: {reason} Re-save the track as valid SRT or WebVTT and retry.")


def _media_folder(conn, row):
    if row["kind"] not in ("movie", "episode"):
        raise HTTPException(404, "Media file does not support local subtitles.")
    library = conn.execute("SELECT path, path_key FROM libraries WHERE id = ?", (row["library_id"],)).fetchone()
    if not library:
        raise HTTPException(404, "Media library was removed. Refresh the library.")
    # Do this before enumeration/stat/realpath on a possibly disconnected network source.
    parent = os.path.dirname(row["path"])
    if not paths.dir_reachable(parent):
        raise _folder_error()
    root, real = _key(library["path"]), os.path.realpath(row["path"])
    if not paths.is_within(root, os.path.normcase(real)):
        raise HTTPException(403, "Media file is outside its configured library folder.")
    if root != library["path_key"] or _key(real) != row["path_key"] or paths.is_link_or_junction(row["path"]):
        raise HTTPException(403, "Media path changed since the last scan. Rescan the library.")
    try:
        if not stat.S_ISREG(os.stat(real).st_mode):
            raise HTTPException(404, "Media file is missing. Reconnect the source or rescan the library.")
    except FileNotFoundError:
        raise HTTPException(404, "Media file is missing. Reconnect the source or rescan the library.") from None
    except OSError:
        raise _folder_error() from None
    return os.path.dirname(real), os.path.splitext(os.path.basename(row["path"]))[0]


def _tags(filename, stem):
    base, extension = os.path.splitext(filename)
    if extension.lower() not in (".srt", ".vtt"):
        return None
    if base.casefold() == stem.casefold():
        return []
    if not base.casefold().startswith(stem.casefold() + "."):
        return None
    tags = base[len(stem) + 1:].split(".")
    return tags if all(TAG.fullmatch(tag) for tag in tags) else None


def _language(tags):
    if not tags:
        return None
    parts = tags[0].replace("_", "-").split("-")
    primary = parts[0].lower()
    primary = LANGUAGE_ALIASES.get(primary, primary)
    if primary not in LANGUAGES:
        return None
    # Common BCP47 filename forms: primary[-Script][-REGION]. Variants stay in the label.
    result = [primary]
    tail = parts[1:]
    if tail and len(tail[0]) == 4 and tail[0].isalpha():
        result.append(tail.pop(0).title())
    if tail and ((len(tail[0]) == 2 and tail[0].isalpha()) or (len(tail[0]) == 3 and tail[0].isdigit())):
        result.append(tail[0].upper())
    return "-".join(result)


def _safe_sidecar(conn, folder, filename):
    candidate = os.path.join(folder, filename)
    if paths.is_link_or_junction(candidate):
        return None
    real = paths.library_real_path(conn, candidate)
    if not real or _key(os.path.dirname(real)) != _key(folder):
        return None
    try:
        info = os.stat(candidate, follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):
            return None
    except FileNotFoundError:
        return None
    return candidate


def _discover(conn, row):
    folder, stem = _media_folder(conn, row)
    found = []
    try:
        with os.scandir(folder) as entries:
            for count, entry in enumerate(entries, 1):
                if count > MAX_DIRECTORY_ENTRIES:
                    raise _folder_error()
                tags = _tags(entry.name, stem)
                if tags is None or not _safe_sidecar(conn, folder, entry.name):
                    continue
                found.append((entry.name, tags))
    except OSError:
        raise _folder_error() from None
    found.sort(key=lambda item: (bool(item[1]), item[0].casefold(), item[0]))
    tracks = []
    for filename, tags in found[:MAX_TRACKS]:
        language = _language(tags)
        track_id = hashlib.sha256(filename.encode("utf-8", errors="surrogatepass")).hexdigest()
        label = " / ".join(tags) if tags else "Default"
        tracks.append({"id": track_id, "label": f"{label} · {filename}", "language": language,
                       "url": f"/api/files/{row['id']}/subtitles/{track_id}"})
    return folder, found[:MAX_TRACKS], tracks


def discover_tracks(conn, row):
    return {"tracks": _discover(conn, row)[2]}


def read_track(conn, row, track_id):
    if not TRACK_ID.fullmatch(track_id):
        raise HTTPException(404, "Unknown subtitle track. Refresh the subtitle list and select a track.")
    folder, found, tracks = _discover(conn, row)
    filename = next((name for (name, _), track in zip(found, tracks) if track["id"] == track_id), None)
    if filename is None:
        raise HTTPException(404, "Subtitle track is missing or changed. Refresh the subtitle list and retry.")
    try:
        candidate = _safe_sidecar(conn, folder, filename)
        if candidate is None:
            raise HTTPException(404, "Subtitle track is missing or changed. Refresh the subtitle list.")
        before = os.stat(candidate, follow_symlinks=False)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        with os.fdopen(os.open(candidate, flags), "rb") as source:
            opened = os.fstat(source.fileno())
            if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(before, opened):
                raise HTTPException(409, "Subtitle file changed while opening. Refresh the subtitle list and retry.")
            if opened.st_size > MAX_SUBTITLE_BYTES:
                raise HTTPException(413, "Subtitle file is too large. Use a track smaller than 2 MiB.")
            data = source.read(MAX_SUBTITLE_BYTES + 1)
            # Recheck both handles and confinement after the bounded read, before returning any content.
            current_folder, _ = _media_folder(conn, row)
            if _key(current_folder) != _key(folder) or _safe_sidecar(conn, folder, filename) is None \
                    or not os.path.samestat(opened, os.stat(candidate, follow_symlinks=False)):
                raise HTTPException(409, "Subtitle file changed while reading. Refresh the subtitle list and retry.")
    except FileNotFoundError:
        raise HTTPException(404, "Subtitle file is missing. Refresh the subtitle list and retry.") from None
    except OSError:
        raise HTTPException(503, "Subtitle file cannot be read. Check source permissions and connection, then retry.") from None
    if len(data) > MAX_SUBTITLE_BYTES:
        raise HTTPException(413, "Subtitle file is too large. Use a track smaller than 2 MiB.")
    return normalize_vtt(data, os.path.splitext(filename)[1].lower())


class _SafeText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []

    def handle_starttag(self, tag, attrs):
        if tag in ("b", "i", "u"):
            self.output.append(f"<{tag}>")
        elif tag == "br":
            self.output.append("\n")

    def handle_endtag(self, tag):
        if tag in ("b", "i", "u"):
            self.output.append(f"</{tag}>")

    def handle_data(self, data):
        # In particular, escape '>' so payload text can never create another '-->' cue header.
        # HTML entities can introduce controls after the input itself has already been validated.
        data = data.replace("\r\n", "\n").replace("\r", "\n")
        data = "".join(char for char in data if ord(char) >= 32 or char in "\n\t")
        self.output.append(html.escape(data, quote=False))


def _timestamp(value):
    parts = value.replace(",", ".").split(":")
    if len(parts) == 2:
        parts.insert(0, "0")
    hours, minutes = int(parts[0]), int(parts[1])
    seconds, millis = map(int, parts[2].split("."))
    total = ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis
    return total, f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def normalize_vtt(data, extension):
    try:
        if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
            text = data.decode("utf-16")
        else:
            try:
                text = data.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = data.decode("cp1252")
    except UnicodeError:
        raise _invalid("unsupported or damaged text encoding.") from None
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if any(ord(char) < 32 and char not in "\n\t" for char in text):
        raise _invalid("binary data or unsupported control characters.")
    is_vtt = extension == ".vtt"
    if is_vtt:
        header, _, text = text.partition("\n")
        if not re.fullmatch(r"WEBVTT(?:[ \t]+[^\n]*)?", header) or "-->" in header:
            raise _invalid("missing WEBVTT header.")
        # A header must be followed by a blank line, not an unseparated cue.
        if text and not text.startswith("\n"):
            raise _invalid("expected a blank line after the WEBVTT header.")
    cues = []
    for block in re.split(r"\n[ \t]*\n", text.strip("\n \t")):
        if not block:
            continue
        lines = block.split("\n")
        if is_vtt and (lines[0] in ("STYLE", "REGION") or re.match(r"NOTE(?:[ \t]|$)", lines[0])):
            continue
        timing = VTT_TIMING if is_vtt else SRT_TIMING
        match = timing.fullmatch(lines[0].strip())
        if not match and len(lines) > 1 and "-->" not in lines[0] and (is_vtt or lines[0].strip().isdigit()):
            lines = lines[1:]
            match = timing.fullmatch(lines[0].strip())
        if not match or len(lines) < 2 or not "\n".join(lines[1:]).strip():
            raise _invalid("a cue has missing text or malformed timing.")
        start, start_text = _timestamp(match[1])
        end, end_text = _timestamp(match[2])
        if end <= start or (is_vtt and "-->" in (match[3] or "")):
            raise _invalid("cue end must be after its start, with valid timing.")
        sanitizer = _SafeText()
        try:
            sanitizer.feed("\n".join(lines[1:]))
            sanitizer.close()
        except (AssertionError, ValueError):  # HTMLParser rejects malformed marked declarations.
            raise _invalid("malformed cue markup.") from None
        # Consecutive <br>s or removed tags must not introduce a new WebVTT block.
        payload = re.sub(r"\n(?:[ \t]*\n)+", "\n", "".join(sanitizer.output)).strip("\n")
        if not payload.strip():
            raise _invalid("a cue contains no displayable text.")
        cues.append(f"{start_text} --> {end_text}\n{payload}")
        if len(cues) > MAX_CUES:
            raise HTTPException(413, "Subtitle has too many cues. Split it into tracks of at most 10,000 cues.")
    if not cues:
        raise _invalid("no subtitle cues were found.")
    return "WEBVTT\n\n" + "\n\n".join(cues) + "\n"
