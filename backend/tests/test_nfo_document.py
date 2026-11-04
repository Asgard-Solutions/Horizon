"""Disposable filesystem tests; never access a configured library or database."""
import hashlib
import errno
import os
import stat
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from xml.dom import minidom

import pytest

from mediacenter import nfo_document as nfo


@pytest.fixture
def document(tmp_path):
    path = tmp_path / "movie.nfo"
    path.write_bytes(b'<movie><title>Original</title></movie>')
    return path, [str(tmp_path)]


def read(document, root="movie"):
    path, roots = document
    return nfo.read_document(str(path), roots, root)


def save(document, fields=None, revision=None, root="movie"):
    path, roots = document
    current = read(document, root)
    return nfo.save_document(str(path), roots, revision or current["revision"],
                             current["fields"] if fields is None else fields, root)


def test_read_defaults_and_exact_byte_revision(document):
    result = read(document)
    assert result == {"revision": hashlib.sha256(document[0].read_bytes()).hexdigest(),
                      "fields": {"title": "Original", "sort_title": "", "year": None,
                                 "plot": "", "tagline": "", "premiered": "", "genres": [],
                                 "cast": [], "rating": None, "ids": {}, "set": ""}}
    assert nfo.NfoError("example").status == 400


@pytest.mark.parametrize('root', ['movie', 'tvshow', 'episodedetails'])
def test_combination_nfo_keeps_links_comments_and_original_backup(document, root):
    trailer=b'\r\nhttps://www.themoviedb.org/movie/123\r\nhttps://www.imdb.com/title/tt1234567\r\n'
    original=f'<{root}><title>Local title</title><!--keep--><custom>Keep me</custom></{root}>'.encode()+trailer
    document[0].write_bytes(original)
    current=read(document,root)
    result=save(document,{**current['fields'],'title':'Changed title'},root=root)
    assert document[0].read_bytes().endswith(trailer)
    assert b'<!--keep--><custom>Keep me</custom>' in document[0].read_bytes()
    assert Path(result['backup_path']).read_bytes()==original
    assert read(document,root)['fields']['title']=='Changed title'


@pytest.mark.parametrize('trailer', [b'\nnot a metadata URL', b'\nhttps://example.test/a\n<movie/>', b'\nftp://example.test/a'])
def test_combination_nfo_does_not_accept_arbitrary_trailing_content(document,trailer):
    original=b'<movie><title>Local title</title></movie>'+trailer
    document[0].write_bytes(original)
    with pytest.raises(nfo.NfoError):read(document)
    assert document[0].read_bytes()==original


def test_preserve_unknown_xml_and_reconcile_kodi_fields(document):
    path, _ = document
    original = b'''<?xml version="1.0"?><!--outside--><movie custom="keep">
<!--inside--><title lang="en">Original</title><year>2000</year><premiered>2000-01-01</premiered>
<rating>7</rating><ratings><rating name="imdb" max="100" default="true"><value>70</value><votes>42</votes><extra/></rating><rating name="other" max="10"><value>3</value></rating></ratings>
<uniqueid type="imdb" default="true">tt123</uniqueid><uniqueid type="custom">opaque</uniqueid>
<runtime>98</runtime><resume><position>31</position></resume><season>2</season><episode>3</episode>
<streamdetails><video codec="hevc"/></streamdetails><custom a="b"><nested/></custom>
<actor><name>A</name><role>B</role><thumb>local.jpg</thumb><order>1</order></actor>
<set><name>Old</name><overview>Keep set overview</overview></set></movie>'''
    path.write_bytes(original)
    fields = read(document)["fields"]
    fields.update(title="Edited & safe", year=2024, premiered="2024-02-29", rating=8.5,
                  ids={"imdb": "tt456", "tmdb": "123"}, set="New")
    result = save(document, fields)
    assert Path(result["backup_path"]).read_bytes() == original
    text = path.read_text(encoding="utf-8")
    dom = minidom.parseString(text)
    assert dom.documentElement.getAttribute("custom") == "keep"
    for fragment in ('<!--outside-->', '<!--inside-->', '<runtime>98</runtime>',
                     '<position>31</position>', '<season>2</season>', '<episode>3</episode>',
                     'codec="hevc"', '<custom a="b"><nested/></custom>', '<thumb>local.jpg</thumb>',
                     '<overview>Keep set overview</overview>', '<uniqueid type="custom">opaque</uniqueid>',
                     '<votes>42</votes>', '<extra/>', '<value>85</value>', '<value>3</value>'):
        assert fragment in text
    assert '<title lang="en">Edited &amp; safe</title>' in text
    assert read(document)["fields"] == result["fields"] == fields


def test_all_editable_fields_roundtrip_and_unique_backups(document):
    fields = {"title": "New", "sort_title": "Sort", "year": 2020, "plot": "Plot\nline",
              "tagline": "Tag", "premiered": "2020-12-31", "genres": ["Drama", "Comedy"],
              "cast": [{"name": "Actor", "role": "Lead"}], "rating": 0.0,
              "ids": {"imdb": "tt12345", "tmdb": "42", "tvdb": "10"}, "set": "Collection"}
    first = save(document, fields)
    previous = document[0].read_bytes()
    fields["title"] = "Again"
    second = save(document, fields)
    assert first["backup_path"] != second["backup_path"]
    assert Path(second["backup_path"]).read_bytes() == previous
    assert read(document)["fields"] == fields
    assert second["revision"] == hashlib.sha256(document[0].read_bytes()).hexdigest()


def test_conflict_does_not_write_or_create_backup(document):
    before = read(document)
    changed = b'<movie><title>Other application</title></movie>'
    document[0].write_bytes(changed)
    with pytest.raises(nfo.NfoError) as error:
        save(document, before["fields"], before["revision"])
    assert error.value.status == 409
    assert document[0].read_bytes() == changed
    assert list(document[0].parent.iterdir()) == [document[0]]


@pytest.mark.parametrize("field,value", [
    ("title", " "), ("title", "a" * 501), ("title", 1), ("plot", "x" * 50001),
    ("plot", "bad\x00xml"), ("sort_title", "x" * 501), ("tagline", "x" * 501),
    ("year", True), ("year", 2020.0), ("year", 1799), ("year", 2201),
    ("premiered", "2023-02-29"), ("premiered", "20200101"),
    ("genres", ["x"] * 13), ("genres", ["x" * 61]), ("genres", "Drama"),
    ("cast", [{"name": "x", "role": "y"}] * 31),
    ("cast", [{"name": "x" * 201, "role": "y"}]), ("cast", [{"name": "x", "extra": "y"}]),
    ("rating", float("nan")), ("rating", float("inf")), ("rating", -1), ("rating", 11),
    ("rating", True), ("rating", "8"), ("ids", {"imdb": "123"}),
    ("rating", 10 ** 1000),
    ("ids", {"tmdb": "-2"}), ("ids", {"tvdb": "１２"}), ("ids", {"unknown": "12"}),
    ("set", "x" * 121), ("raw_xml", "<movie/>"),
])
def test_invalid_edit_is_422_without_any_writes(document, field, value):
    original = document[0].read_bytes()
    fields = read(document)["fields"]
    fields[field] = value
    with pytest.raises(nfo.NfoError) as error:
        save(document, fields)
    assert error.value.status == 422
    assert document[0].read_bytes() == original
    assert list(document[0].parent.iterdir()) == [document[0]]


@pytest.mark.parametrize("content", [b'<movie>', b'<musicvideo/>', b'<tvshow/>',
    b'<!DOCTYPE movie><movie/>',
    b'<!DOCTYPE movie [<!ENTITY x "bad">]><movie><title>&x;</title></movie>',
    '<!DOCTYPE movie><movie/>'.encode("utf-16"), b'<movie>' + b' ' * 1048576 + b'</movie>'])
def test_unsafe_or_unsupported_xml_is_rejected(document, content):
    document[0].write_bytes(content)
    with pytest.raises(nfo.NfoError) as error:
        read(document)
    assert error.value.status == 422


def test_missing_directory_escape_and_extension(document, tmp_path):
    path, roots = document
    for target, allowed, status in ((path.with_name("missing.nfo"), roots, 404),
                                    (path.parent, roots, 422),
                                    (path, [str(tmp_path / "other")], 422),
                                    (path, [], 422)):
        with pytest.raises(nfo.NfoError) as error:
            nfo.read_document(str(target), allowed, "movie")
        assert error.value.status == status
    media = path.with_suffix(".mkv")
    media.write_bytes(path.read_bytes())
    with pytest.raises(nfo.NfoError):
        nfo.read_document(str(media), roots, "movie")


def test_hardlinked_nfo_rejected(document):
    alias = document[0].with_name("alias.nfo")
    os.link(document[0], alias)
    with pytest.raises(nfo.NfoError) as error:
        read(document)
    assert error.value.status == 422


@pytest.mark.parametrize("directory", [False, True])
def test_symlink_rejected(document, directory):
    path, roots = document
    alias = path.parent / ("alias" if directory else "alias.nfo")
    try:
        alias.symlink_to(path.parent if directory else path, target_is_directory=directory)
    except OSError:
        pytest.skip("Creating symlinks requires platform permission")
    with pytest.raises(nfo.NfoError) as error:
        nfo.read_document(str(alias / path.name if directory else alias), roots, "movie")
    assert error.value.status == 422


def test_failed_replace_leaves_original_backup_and_no_temp(document, monkeypatch):
    original = document[0].read_bytes()
    fields = read(document)["fields"]
    fields["title"] = "Edited"

    def fail_replace(*args, **kwargs):
        raise PermissionError("locked by another application")

    monkeypatch.setattr(nfo.os, "replace", fail_replace)
    with pytest.raises(nfo.NfoError, match="(?i)(permission|read.only|writ|clos|access)"):
        save(document, fields)
    assert document[0].read_bytes() == original
    backups = list(document[0].parent.glob("*.bak"))
    assert len(backups) == 1 and backups[0].read_bytes() == original
    assert len(list(document[0].parent.iterdir())) == 2


def test_two_simultaneous_saves_have_one_conflict(document):
    before = read(document)

    def attempt(title):
        fields = {**before["fields"], "title": title}
        try:
            return save(document, fields, before["revision"])
        except nfo.NfoError as error:
            return error.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["First", "Second"]))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert 409 in results
    assert len(list(document[0].parent.glob("*.bak"))) == 1


@pytest.mark.parametrize("root", ["tvshow", "episodedetails"])
def test_nonmovie_preserves_episode_fields_and_rejects_set(document, root):
    document[0].write_text(f'<{root}><title>TV</title><season>1</season><episode>2</episode></{root}>')
    fields = read(document, root)["fields"]
    assert "set" not in fields
    fields["title"] = "Changed"
    result = save(document, fields, root=root)
    assert result["fields"]["title"] == "Changed"
    assert "<season>1</season><episode>2</episode>" in document[0].read_text()
    with pytest.raises(nfo.NfoError) as error:
        save(document, {**fields, "set": "Forbidden"}, root=root)
    assert error.value.status == 422


def test_clear_editable_fields_keeps_other_provider_ids_and_runtime(document):
    document[0].write_bytes(b'''<movie><title>Old</title><year>2020</year>
<premiered>2020-01-01</premiered><rating>7</rating>
<ratings><rating name="imdb" default="true"><value>7</value><votes>25</votes></rating></ratings>
<id>tt123</id><imdbid>tt123</imdbid><uniqueid type="imdb">tt123</uniqueid>
<uniqueid type="other">999</uniqueid><genre>Drama</genre><actor><name>A</name><role>B</role></actor>
<set><name>Collection</name><overview>Preserve me</overview></set><runtime>123</runtime></movie>''')
    fields = {"title": "Still here", "sort_title": "", "year": None, "plot": "", "tagline": "",
              "premiered": "", "genres": [], "cast": [], "rating": None, "ids": {}, "set": ""}
    result = save(document, fields)
    assert read(document)["fields"] == result["fields"] == fields
    text = document[0].read_text()
    assert '<uniqueid type="other">999</uniqueid>' in text
    assert '<runtime>123</runtime>' in text
    assert '<overview>Preserve me</overview>' in text
    assert '<votes>25</votes>' in text


@pytest.mark.parametrize("root,tag", [("movie", "releasedate"), ("tvshow", "premiered"), ("episodedetails", "aired")])
def test_legacy_dates_read_and_reconcile(document, root, tag):
    document[0].write_bytes(f'<{root}><title>Old</title><{tag}>2020-01-01</{tag}></{root}>'.encode())
    fields = read(document, root)["fields"]
    assert fields["premiered"] == "2020-01-01"
    assert fields["year"] == 2020
    fields.update(premiered="2021-03-02", year=2021)
    save(document, fields, root=root)
    assert f'<{tag}>2021-03-02</{tag}>' in document[0].read_text()
    assert read(document, root)["fields"]["premiered"] == "2021-03-02"


@pytest.mark.parametrize("stage", ["backup", "temp"])
def test_failed_write_never_replaces_original(document, monkeypatch, stage):
    original = document[0].read_bytes()
    real_fsync = os.fsync
    calls = 0

    def fsync(fd):
        nonlocal calls
        calls += 1
        if calls == (1 if stage == "backup" else 2):
            raise OSError(errno.ENOSPC, "disposable volume full")
        return real_fsync(fd)

    monkeypatch.setattr(nfo.os, "fsync", fsync)
    with pytest.raises(nfo.NfoError) as error:
        save(document, {"title": "Change"})
    assert error.value.status == 503
    assert document[0].read_bytes() == original
    assert len(list(document[0].parent.glob("*.bak"))) == 1
    assert not list(document[0].parent.glob("*.tmp"))


def test_readonly_nfo_has_actionable_error_and_no_backup(document):
    path = document[0]
    previous = path.stat().st_mode
    path.chmod(stat.S_IREAD)
    try:
        with pytest.raises(nfo.NfoError, match="(?i)(read.only|permission)") as error:
            save(document, {"title": "Change"})
        assert error.value.status == 403
        assert not list(path.parent.glob("*.bak"))
    finally:
        path.chmod(previous)


def test_offline_storage_is_actionable(document, monkeypatch):
    def offline(self):
        raise OSError(errno.ENETDOWN, "disposable offline storage")

    monkeypatch.setattr(nfo._Guard, "read", offline)
    with pytest.raises(nfo.NfoError, match="(?i)(reconnect|share|drive)") as error:
        read(document)
    assert error.value.status == 503


def test_windows_offline_share_is_not_reported_as_missing_file(document, monkeypatch):
    def offline(self):
        error = FileNotFoundError(errno.ENOENT, "network path unavailable")
        error.winerror = 53
        raise error

    monkeypatch.setattr(nfo._Guard, "read", offline)
    with pytest.raises(nfo.NfoError, match="(?i)(reconnect|share|drive)") as error:
        read(document)
    assert error.value.status == 503


@pytest.mark.skipif(os.name != "nt", reason="Windows junction and directory handle semantics")
def test_junction_root_and_parent_are_rejected(document):
    path, roots = document
    alias = path.parent / "junction"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(alias), str(path.parent)],
                   check=True, capture_output=True)
    for configured in (roots, [str(alias)]):
        with pytest.raises(nfo.NfoError) as error:
            nfo.read_document(str(alias / path.name), configured, "movie")
        assert error.value.status == 422


@pytest.mark.skipif(os.name != "nt", reason="Windows directory handle semantics")
def test_windows_guard_blocks_parent_rename_during_save(document, monkeypatch):
    parent = document[0].parent
    moved = parent.with_name(parent.name + "-moved")
    real_write = nfo._write

    def write(fd, content):
        with pytest.raises(PermissionError):
            parent.rename(moved)
        real_write(fd, content)

    monkeypatch.setattr(nfo, "_write", write)
    save(document, {"title": "Safely edited"})
    assert read(document)["fields"]["title"] == "Safely edited"
    assert not moved.exists()


def test_temp_cleanup_does_not_delete_replaced_temp(document, monkeypatch):
    intruder = None

    def replace(src, dst, **kwargs):
        nonlocal intruder
        intruder = Path(src) if os.name == "nt" else document[0].parent / src
        intruder.unlink()
        intruder.write_bytes(b"not our temp file")
        raise PermissionError("injected failure after temporary path replacement")

    monkeypatch.setattr(nfo.os, "replace", replace)
    with pytest.raises(nfo.NfoError):
        save(document, {"title": "Change"})
    assert intruder.read_bytes() == b"not our temp file"
    assert document[0].read_bytes() == b'<movie><title>Original</title></movie>'


def test_deep_xml_reports_validation_error_instead_of_recursion_failure(document):
    document[0].write_bytes(b'<movie><title>Original</title>' + b'<nested>' * 1100 + b'</nested>' * 1100 + b'</movie>')
    with pytest.raises(nfo.NfoError) as error:
        save(document, {"title": "Change"})
    assert error.value.status == 422
    assert not list(document[0].parent.glob("*.bak"))


@pytest.mark.parametrize("root", ["video", None, []])
def test_invalid_expected_root_is_validation_error(document, root):
    with pytest.raises(nfo.NfoError) as error:
        read(document, root)
    assert error.value.status == 422


def test_external_change_during_save_is_rechecked_before_replace(document, monkeypatch):
    path, _ = document
    original = path.read_bytes()
    changed = b'<movie><title>Other app during save</title></movie>'
    real_write = nfo._write
    calls = 0

    def write(fd, content):
        nonlocal calls
        real_write(fd, content)
        calls += 1
        if calls == 1:
            # Rename the open entry aside, as an editor can do even while a
            # read handle is held, then install a genuinely different file.
            path.rename(path.with_name("other-app-original.nfo"))
            path.write_bytes(changed)

    monkeypatch.setattr(nfo, "_write", write)
    with pytest.raises(nfo.NfoError) as error:
        save(document, {"title": "Horizon edit"})
    assert error.value.status == 409
    assert path.read_bytes() == changed
    backups = list(path.parent.glob("*.bak"))
    assert len(backups) == 1 and backups[0].read_bytes() == original
    assert not list(path.parent.glob("*.tmp"))


def test_backup_name_collision_never_overwrites_existing_file(document, monkeypatch):
    class FixedUUID:
        hex = "a" * 32

    monkeypatch.setattr(nfo.uuid, "uuid4", FixedUUID)
    collision = document[0].with_name(document[0].name + ".horizon-" + "a" * 32 + ".bak")
    collision.write_bytes(b"existing backup")
    with pytest.raises(nfo.NfoError):
        save(document, {"title": "Change"})
    assert collision.read_bytes() == b"existing backup"
    assert document[0].read_bytes() == b'<movie><title>Original</title></movie>'
    assert not list(document[0].parent.glob("*.tmp"))


def test_missing_save_does_not_create_nfo(document):
    current = read(document)
    document[0].unlink()
    with pytest.raises(nfo.NfoError) as error:
        nfo.save_document(str(document[0]), document[1], current["revision"], current["fields"], "movie")
    assert error.value.status == 404
    assert not list(document[0].parent.iterdir())


def test_save_does_not_touch_media_or_artwork(document):
    media = document[0].with_suffix(".mkv")
    art = document[0].with_name("poster.jpg")
    media.write_bytes(b"disposable fake video")
    art.write_bytes(b"disposable fake artwork")
    save(document, {"title": "Changed"})
    assert media.read_bytes() == b"disposable fake video"
    assert art.read_bytes() == b"disposable fake artwork"


@pytest.mark.parametrize("revision", [None, "", "a" * 63, "z" * 64])
def test_invalid_revision_cannot_write(document, revision):
    with pytest.raises(nfo.NfoError) as error:
        nfo.save_document(str(document[0]), document[1], revision, {"title": "Change"}, "movie")
    assert error.value.status == 422
    assert list(document[0].parent.iterdir()) == [document[0]]


@pytest.mark.parametrize("fields", [None, [], {}, {"plot": "no title"}])
def test_invalid_or_missing_edit_fields_cannot_write(document, fields):
    current = read(document)
    with pytest.raises(nfo.NfoError) as error:
        nfo.save_document(str(document[0]), document[1], current["revision"], fields, "movie")
    assert error.value.status == 422
    assert list(document[0].parent.iterdir()) == [document[0]]


def test_output_size_limit_applies_before_backup(document):
    document[0].write_bytes(b'<movie><title>Original</title><unknown>' + b'x' * 1000000 + b'</unknown></movie>')
    with pytest.raises(nfo.NfoError) as error:
        save(document, {"title": "Change", "plot": "x" * 50000})
    assert error.value.status == 422
    assert not list(document[0].parent.glob("*.bak"))


@pytest.mark.skipif(os.name != "nt", reason="Windows namespace handling")
@pytest.mark.parametrize("suffix", [":stream", ".", " "])
def test_windows_ambiguous_paths_rejected(document, suffix):
    with pytest.raises(nfo.NfoError) as error:
        nfo.read_document(str(document[0]) + suffix, document[1], "movie")
    assert error.value.status == 422


@pytest.mark.skipif(os.name == "nt", reason="POSIX no-follow directory descriptors")
def test_posix_parent_swap_aborts_without_editing_relocated_nfo(document, monkeypatch):
    parent = document[0].parent
    moved = parent.with_name(parent.name + "-moved")
    real_write = nfo._write
    original = document[0].read_bytes()
    calls = 0

    def write(fd, content):
        nonlocal calls
        real_write(fd, content)
        calls += 1
        if calls == 1:
            parent.rename(moved)
            parent.mkdir()
            (parent / "movie.nfo").write_bytes(b'<movie><title>Different directory</title></movie>')

    monkeypatch.setattr(nfo, "_write", write)
    with pytest.raises(nfo.NfoError) as error:
        save(document, {"title": "Change"})
    assert error.value.status == 409
    assert (moved / "movie.nfo").read_bytes() == original
    assert (parent / "movie.nfo").read_bytes() == b'<movie><title>Different directory</title></movie>'
    assert not list(moved.glob("*.tmp"))


def windows_security(path):
    """Read Windows owner/group/DACL independently of the editor implementation."""
    import ctypes
    from ctypes import wintypes

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    get = advapi.GetNamedSecurityInfoW
    get.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD] + [ctypes.POINTER(ctypes.c_void_p)] * 5
    get.restype = wintypes.DWORD
    descriptor = ctypes.c_void_p()
    result = get(str(path), 1, 7, None, None, None, None, ctypes.byref(descriptor))
    if result:
        raise ctypes.WinError(result)
    convert = advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW
    convert.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                        ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(wintypes.DWORD)]
    convert.restype = wintypes.BOOL
    free = ctypes.WinDLL("kernel32").LocalFree
    free.argtypes = [ctypes.c_void_p]
    free.restype = ctypes.c_void_p
    text = wintypes.LPWSTR()
    try:
        if not convert(descriptor, 1, 7, ctypes.byref(text), None):
            raise ctypes.WinError(ctypes.get_last_error())
        return text.value
    finally:
        if text:
            free(text)
        free(descriptor)


@pytest.mark.skipif(os.name != "nt", reason="Windows DACL preservation")
def test_custom_windows_security_survives_atomic_save(document):
    path = document[0]
    subprocess.run(["icacls", str(path), "/inheritance:d", "/grant", "*S-1-1-0:(R)"],
                   check=True, capture_output=True)
    before = windows_security(path)
    assert "D:P" in before
    result = save(document, {"title": "Security preserved"})
    assert windows_security(path) == before
    assert read(document)["fields"]["title"] == "Security preserved"
    assert Path(result["backup_path"]).read_bytes() == b'<movie><title>Original</title></movie>'


@pytest.mark.skipif(os.name != "nt", reason="Windows DACL preservation")
def test_unsupported_windows_security_copy_aborts_without_acl_loss(document, monkeypatch):
    path = document[0]
    original = path.read_bytes()
    before = windows_security(path)

    def unsupported(*args):
        raise nfo.NfoError("Cannot preserve Windows security on this drive/share. Save in the originating editor.", 503)

    monkeypatch.setattr(nfo, "_win_preserve_security", unsupported, raising=False)
    with pytest.raises(nfo.NfoError, match="(?i)(security|permission|ACL)") as error:
        save(document, {"title": "Change"})
    assert error.value.status == 503
    assert path.read_bytes() == original
    assert windows_security(path) == before
    assert len(list(path.parent.glob("*.bak"))) == 1
    assert not list(path.parent.glob("*.tmp"))


@pytest.mark.skipif(os.name != "nt", reason="Windows security preservation")
def test_external_change_during_security_copy_is_a_conflict(document, monkeypatch):
    path = document[0]
    real_copy = nfo._win_preserve_security
    changed = b'<movie><title>Changed while copying permissions</title></movie>'

    def copy(source, target):
        real_copy(source, target)
        path.rename(path.with_name("other-app-old.nfo"))
        path.write_bytes(changed)

    monkeypatch.setattr(nfo, "_win_preserve_security", copy)
    with pytest.raises(nfo.NfoError) as error:
        save(document, {"title": "Horizon change"})
    assert error.value.status == 409
    assert path.read_bytes() == changed
    assert not list(path.parent.glob("*.tmp"))
