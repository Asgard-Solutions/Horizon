"""Local sidecar contract, using only disposable media and the test database."""
import codecs
import hashlib
import os
import re

import pytest

from mediacenter.db import connect, set_setting
from tests.conftest import write


SRT = "1\r\n00:00:01,250 --> 00:00:03,500\r\nHello <i>world</i>\r\nSecond line\r\n"
VTT = "WEBVTT\n\n00:01.250 --> 00:03.500\nHello <i>world</i>\nSecond line\n"
NORMALIZED = "WEBVTT\n\n00:00:01.250 --> 00:00:03.500\nHello <i>world</i>\nSecond line\n"


@pytest.fixture
def movie(host, library, media_root):
    row = next(m for m in host.get("/api/movies").json() if m["title"] == "Sample Movie")
    return row["file_id"], media_root / "Movies" / "Sample Movie (2024).mp4"


def endpoint(file_id):
    return f"/api/files/{file_id}/subtitles"


def sidecar(media, suffix=".srt", text=SRT, encoding="utf-8"):
    return write(media.with_name(media.stem + suffix), text.encode(encoding))


def tracks(host, file_id):
    response = host.get(endpoint(file_id))
    assert response.status_code == 200, response.text
    return response.json()["tracks"]


def only_track(host, file_id):
    result = tracks(host, file_id)
    assert len(result) == 1
    return result[0]


def assert_error(response, status, hint):
    assert response.status_code == status, response.text
    assert hint.lower() in response.json()["detail"].lower()


def test_discovery_is_exact_deterministic_and_keeps_filename(host, movie):
    file_id, media = movie
    for suffix in (".fr.commentary.vtt", ".EN.forced.SRT", ".vtt", ".srt"):
        sidecar(media, suffix)
    for suffix in ("2.en.srt", "-en.srt", ".srt.bak", "..en.srt", ".en..srt", ".ass"):
        sidecar(media, suffix)
    write(media.parent / "Subs" / (media.stem + ".srt"), SRT.encode())
    result = tracks(host, file_id)
    expected = [media.stem + s for s in (".srt", ".vtt", ".EN.forced.SRT", ".fr.commentary.vtt")]
    assert [t["label"].split(" · ")[-1] for t in result] == expected
    assert [t["language"] for t in result] == [None, None, "en", "fr"]
    assert result == tracks(host, file_id)
    for track in result:
        assert set(track) == {"id", "label", "language", "url"}
        assert len(track["id"]) == 64 and int(track["id"], 16) >= 0
        assert track["url"] == endpoint(file_id) + "/" + track["id"]
        assert str(media.parent) not in str(track)


@pytest.mark.parametrize("tag,language", [
    ("eng", "en"), ("spa", "es"), ("fre", "fr"), ("fra", "fr"), ("ger", "de"), ("deu", "de"),
    ("por-BR", "pt-BR"), ("EN-us", "en-US"), ("zho-Hant", "zh-Hant"), ("jpn", "ja"),
    ("eng-latn-us", "en-Latn-US"), ("en-US-Latn", "en-US"),
    ("nld", "nl"), ("dut", "nl"), ("ces", "cs"), ("cze", "cs"), ("und", None),
    ("zz", None), ("forced", None), ("sdh", None),
])
def test_language_tags_normalize_known_codes(host, movie, tag, language):
    file_id, media = movie
    path = sidecar(media, f".{tag}.forced.srt")
    track = only_track(host, file_id)
    assert track["language"] == language
    assert path.name in track["label"]


def test_episode_discovery_and_ids_are_file_scoped(host, library, media_root):
    show = next(s for s in host.get("/api/shows").json() if s["title"] == "Sample Show")
    episodes = host.get(f"/api/shows/{show['id']}").json()["seasons"][0]["episodes"]
    for episode in episodes:
        media = media_root / "TV" / "Sample Show" / "Season 01" / episode["filename"]
        sidecar(media, ".eng.srt")
    first, second = [only_track(host, e["file_id"]) for e in episodes]
    assert first["language"] == "en" and second["language"] == "en"
    assert episodes[0]["filename"].rsplit(".", 1)[0] in first["label"]
    assert_error(host.get(endpoint(episodes[1]["file_id"]) + "/" + first["id"]), 404, "subtitle")


@pytest.mark.parametrize("text,encoding", [(SRT, "utf-8"), (SRT, "utf-8-sig"), (SRT, "utf-16"),
                                           (SRT, "utf-16-be"), (VTT, "utf-8-sig")])
def test_conversion_normalizes_timing_encoding_and_newlines(host, movie, text, encoding):
    file_id, media = movie
    path = sidecar(media, ".vtt" if text == VTT else ".srt", text, encoding)
    if encoding == "utf-16-be":
        path.write_bytes(codecs.BOM_UTF16_BE + path.read_bytes())
    original = path.read_bytes()
    response = host.get(only_track(host, file_id)["url"])
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "text/vtt; charset=utf-8"
    assert response.headers["cache-control"] == "no-store"
    assert response.content == NORMALIZED.encode("utf-8")
    assert path.read_bytes() == original


def test_cp1252_fallback_preserves_windows_punctuation(host, movie):
    file_id, media = movie
    sidecar(media, text="1\n00:00:00,000 --> 00:00:01,000\n“Café”—€\n", encoding="cp1252")
    response = host.get(only_track(host, file_id)["url"])
    assert response.status_code == 200
    assert "“Café”—€" in response.content.decode("utf-8")


@pytest.mark.parametrize("suffix,source", [
    (".srt", "1\n00:00:00,000 --> 00:00:02,000\n"),
    (".vtt", "WEBVTT\n\nidentifier\n00:00.000 --> 00:02.000 align:start\n"),
])
def test_only_safe_styling_and_text_survive(host, movie, suffix, source):
    file_id, media = movie
    payload = '<b onclick="alert(1)">Bold</b> <i>italics</i> <u>under</u>\n<script>alert(1)</script>' \
              '<img src=x onerror=alert(1)><a href="javascript:alert(1)">link</a>\n' \
              '00:00:00.000 --> 00:00:01.000 &amp; &lt;script&gt;'
    sidecar(media, suffix, source + payload)
    response = host.get(only_track(host, file_id)["url"])
    assert response.status_code == 200, response.text
    assert '<b>Bold</b> <i>italics</i> <u>under</u>' in response.text
    assert response.text.count("-->") == 1
    assert all(s not in response.text for s in ("<script", "<img", "<a ", "onclick", "onerror", "javascript:"))
    assert "\nalert(1)link\n" in response.text


@pytest.mark.parametrize("suffix,text", [
    (".srt", ""), (".srt", "not subtitles"),
    (".srt", "1\n00:61:00,000 --> 00:62:00,000\nNo"),
    (".srt", "1\n00:00:02,000 --> 00:00:01,000\nBackwards"),
    (".srt", "1\n00:00:01,000 --> 00:00:01,000\nZero"),
    (".srt", "1\n00:00:00,000 --> 00:00:01,000\nValid\n\nWEBVTT\nInjected"),
    (".srt", "1\n00:00:00,000 --> 00:00:01,000\nBad\x00text"),
    (".vtt", "not WebVTT\n\n00:00.000 --> 00:01.000\nNo"),
    (".vtt", "WEBVTT\n\n00:00.000 --> 00:01.000\n"),
])
def test_invalid_tracks_return_actionable_422(host, movie, suffix, text):
    file_id, media = movie
    sidecar(media, suffix, text)
    assert_error(host.get(only_track(host, file_id)["url"]), 422, "subtitle")


def test_vtt_metadata_blocks_are_not_returned_as_cues(host, movie):
    file_id, media = movie
    sidecar(media, ".vtt", "WEBVTT\n\nSTYLE\n::cue {background: url(https://example.com)}\n\n"
            "NOTE comment\nignored\n\nREGION\nid:foo\n\n"
            "cue-name\n00:00.000 --> 00:01.000 position:10%\nText\n")
    response = host.get(only_track(host, file_id)["url"])
    assert response.status_code == 200
    assert response.text == "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nText\n"


def test_accessible_folder_without_matches_is_empty(host, movie):
    assert tracks(host, movie[0]) == []


@pytest.mark.parametrize("resource", ["folder", "media", "sidecar", "library"])
def test_each_get_revalidates_resources(app, host, movie, resource):
    file_id, media = movie
    path = sidecar(media)
    track = only_track(host, file_id)
    if resource == "folder":
        media.parent.rename(media.parent.with_name("offline-movies"))
    elif resource == "media":
        media.unlink()
    elif resource == "sidecar":
        path.unlink()
    else:
        with connect(app.state.config.db_path) as conn:
            conn.execute("DELETE FROM libraries")
    response = host.get(track["url"])
    if resource == "folder":
        assert_error(response, 503, "folder")
        assert_error(host.get(endpoint(file_id)), 503, "folder")
    elif resource == "sidecar":
        assert_error(response, 404, "subtitle")
        assert tracks(host, file_id) == []
    else:
        assert response.status_code == 404
        assert host.get(endpoint(file_id)).status_code == 404


def test_reachability_check_precedes_directory_enumeration(host, movie, monkeypatch):
    from mediacenter import paths
    file_id, media = movie
    sidecar(media)
    track = only_track(host, file_id)
    monkeypatch.setattr(paths, "dir_reachable", lambda _: False)
    def unexpected_scan(*_):
        pytest.fail("scandir must not run on an unreachable folder")
    monkeypatch.setattr(os, "scandir", unexpected_scan)
    assert_error(host.get(endpoint(file_id)), 503, "folder")
    assert_error(host.get(track["url"]), 503, "folder")


def test_directory_permission_failure_is_actionable(host, movie, monkeypatch):
    file_id, _ = movie
    def denied(*_):
        raise PermissionError("private host path must not leak")
    monkeypatch.setattr(os, "scandir", denied)
    response = host.get(endpoint(file_id))
    assert_error(response, 503, "folder")
    assert "private host path" not in response.text


@pytest.mark.parametrize("track_id", ["Sample Movie (2024).srt", "c" * 64, "..%5Csecret.srt", "%2Fetc%2Fpasswd"])
def test_track_ids_cannot_select_arbitrary_paths(host, movie, track_id):
    file_id, media = movie
    sidecar(media)
    response = host.get(endpoint(file_id) + "/" + track_id)
    assert response.status_code in (404, 422)
    assert "WEBVTT" not in response.text


def test_uncatalogued_and_non_video_ids_rejected(app, host, movie):
    file_id, _ = movie
    assert host.get(endpoint(999999)).status_code == 404
    with connect(app.state.config.db_path) as conn:
        conn.execute("UPDATE media_files SET kind = 'image' WHERE id = ?", (file_id,))
    assert_error(host.get(endpoint(file_id)), 404, "media")


def test_media_outside_its_library_is_rejected(app, host, movie, tmp_path):
    file_id, _ = movie
    outside = write(tmp_path / "outside" / "secret.mp4")
    with connect(app.state.config.db_path) as conn:
        conn.execute("UPDATE media_files SET path = ? WHERE id = ?", (str(outside), file_id))
    assert_error(host.get(endpoint(file_id)), 403, "library")


def make_link(link, target):
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"Symlink privilege unavailable: {exc}")


def test_symlink_sidecar_escape_not_listed_or_served(host, movie, tmp_path):
    file_id, media = movie
    path = media.with_suffix(".srt")
    outside = write(tmp_path / "secret.srt", SRT.encode())
    make_link(path, outside)
    assert tracks(host, file_id) == []
    forged = hashlib.sha256(path.name.encode()).hexdigest()
    assert host.get(endpoint(file_id) + "/" + forged).status_code == 404


def test_sidecar_replaced_by_symlink_after_discovery_is_rejected(host, movie, tmp_path):
    file_id, media = movie
    path = sidecar(media)
    track = only_track(host, file_id)
    outside = write(tmp_path / "secret.srt", SRT.encode())
    path.unlink()
    make_link(path, outside)
    assert host.get(track["url"]).status_code in (403, 404)


def test_changed_media_target_is_rejected(app, host, movie):
    file_id, media = movie
    sidecar(media)
    track = only_track(host, file_id)
    with connect(app.state.config.db_path) as conn:
        conn.execute("UPDATE media_files SET path_key = 'stale-key' WHERE id = ?", (file_id,))
    assert_error(host.get(track["url"]), 403, "rescan")


def test_both_endpoints_require_viewer_on_every_request(host, movie, lan_client_factory):
    file_id, media = movie
    sidecar(media)
    track = only_track(host, file_id)
    client = lan_client_factory()
    for url in (endpoint(file_id), track["url"]):
        assert client.get(url).status_code == 403
    assert host.post("/api/settings/pin", json={"pin": "48261937"}).status_code == 200
    assert host.post("/api/settings/lan", json={"enabled": True}).status_code == 200
    for url in (endpoint(file_id), track["url"]):
        assert client.get(url).status_code == 401
    paired = client.post("/api/auth/pair", json={"pin": "48261937", "device_name": "subtitle viewer"})
    assert paired.status_code == 200, paired.text
    for url in (endpoint(file_id), track["url"]):
        assert client.get(url).status_code == 200
    device = host.get("/api/devices").json()[0]
    assert host.delete(f"/api/devices/{device['id']}").status_code == 200
    for url in (endpoint(file_id), track["url"]):
        assert client.get(url).status_code == 401


def test_read_size_and_cue_count_are_bounded(host, movie, monkeypatch):
    from mediacenter import subtitles
    file_id, media = movie
    path = sidecar(media)
    track = only_track(host, file_id)
    monkeypatch.setattr(subtitles, "MAX_SUBTITLE_BYTES", 32)
    assert_error(host.get(track["url"]), 413, "subtitle")
    monkeypatch.setattr(subtitles, "MAX_SUBTITLE_BYTES", 4096)
    monkeypatch.setattr(subtitles, "MAX_CUES", 1)
    path.write_bytes((SRT + "\n2\n00:00:04,000 --> 00:00:05,000\nSecond cue").encode())
    assert_error(host.get(track["url"]), 413, "cue")


def test_track_list_is_bounded_and_deterministic(host, movie, monkeypatch):
    from mediacenter import subtitles
    file_id, media = movie
    for suffix in (".fr.srt", ".en.srt", ".srt", ".de.srt"):
        sidecar(media, suffix)
    monkeypatch.setattr(subtitles, "MAX_TRACKS", 2)
    result = tracks(host, file_id)
    assert [r["language"] for r in result] == [None, "de"]
    assert result == tracks(host, file_id)
    monkeypatch.setattr(subtitles, "MAX_DIRECTORY_ENTRIES", 2)
    assert_error(host.get(endpoint(file_id)), 503, "folder")


def test_new_subtitle_preference_is_additive_validated_and_persistent(app, host):
    with connect(app.state.config.db_path) as conn:
        set_setting(conn, "playback_prefs", '{"resume":"auto","skip_seconds":30}')
    prefs = host.get("/api/preferences").json()
    assert prefs["subtitles"] == "off" and prefs["resume"] == "auto" and prefs["skip_seconds"] == 30
    saved = host.put("/api/preferences", json={"subtitles": "auto"})
    assert saved.status_code == 200 and saved.json()["subtitles"] == "auto"
    assert host.get("/api/preferences").json()["subtitles"] == "auto"
    assert host.put("/api/preferences", json={"subtitles": "on"}).status_code == 422
    assert host.put("/api/preferences", json={"subtitles": "off"}).json()["skip_seconds"] == 30


def test_absurd_timestamps_are_invalid_instead_of_server_errors(host, movie):
    file_id, media = movie
    sidecar(media, text="1\n" + "9" * 5000 + ":00:00,000 --> 00:00:01,000\nBad")
    assert_error(host.get(only_track(host, file_id)["url"]), 422, "timing")


def test_break_markup_preserves_line_breaks_without_blank_cue_injection(host, movie):
    file_id, media = movie
    sidecar(media, text="1\n00:00:00,000 --> 00:00:02,000\nOne<br>Two<br/><br>Three")
    response = host.get(only_track(host, file_id)["url"])
    assert response.status_code == 200
    assert response.text == "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nOne\nTwo\nThree\n"


def test_sidecar_swapped_during_open_never_returns_outside_content(host, movie, tmp_path, monkeypatch):
    file_id, media = movie
    path = sidecar(media)
    track = only_track(host, file_id)
    outside = write(tmp_path / "outside.srt", SRT.replace("Hello", "SECRET").encode())
    original_open = os.open
    def swapped_open(name, flags, *args, **kwargs):
        if os.path.normcase(str(name)) == os.path.normcase(str(path)):
            os.replace(outside, path)
        return original_open(name, flags, *args, **kwargs)
    monkeypatch.setattr(os, "open", swapped_open)
    response = host.get(track["url"])
    assert response.status_code == 409
    assert "SECRET" not in response.text


def test_sidecar_read_permission_error_is_actionable(host, movie, monkeypatch):
    file_id, media = movie
    path = sidecar(media)
    track = only_track(host, file_id)
    original_open = os.open
    def denied_open(name, flags, *args, **kwargs):
        if os.path.normcase(str(name)) == os.path.normcase(str(path)):
            raise PermissionError("sensitive host path")
        return original_open(name, flags, *args, **kwargs)
    monkeypatch.setattr(os, "open", denied_open)
    response = host.get(track["url"])
    assert_error(response, 503, "permissions")
    assert "sensitive host path" not in response.text


def test_detached_library_cannot_borrow_another_library_authorization(app, host, movie, tmp_path):
    file_id, media = movie
    sidecar(media)
    track = only_track(host, file_id)
    other = write(tmp_path / "other" / media.name)
    sidecar(other)
    assert host.post("/api/libraries", json={"path": str(other.parent), "scan": False}).status_code == 200
    with connect(app.state.config.db_path) as conn:
        conn.execute("UPDATE media_files SET path = ?, path_key = ? WHERE id = ?",
                     (str(other), os.path.normcase(os.path.realpath(other)), file_id))
    assert_error(host.get(track["url"]), 403, "library")


@pytest.mark.parametrize("breaks", ["&#13;&#13;", "&#13; &#13; &#13;"])
def test_encoded_controls_cannot_create_new_vtt_blocks(host, movie, breaks):
    file_id, media = movie
    sidecar(media, text="1\n00:00:00,000 --> 00:00:02,000\n"
            f"Text{breaks}STYLE&#13;::cue {{color:red}}&#0;&#12;&#10;&#10;"
            "00:00:00.000 --&gt; 00:00:01.000")
    response = host.get(only_track(host, file_id)["url"])
    assert response.status_code == 200
    assert "\r" not in response.text and "\x00" not in response.text and "\x0c" not in response.text
    assert response.text.count("\n\n") == 1
    assert not re.search(r"\n[ \t]*\n", response.text.split("\n\n", 1)[1])
    assert response.text.count("-->") == 1


def test_malformed_html_declarations_are_invalid_instead_of_server_errors(host, movie):
    file_id, media = movie
    sidecar(media, text="1\n00:00:00,000 --> 00:00:01,000\n<![BOGUS[boom]]>")
    assert_error(host.get(only_track(host, file_id)["url"]), 422, "markup")
