"""Windows path semantics, exercised with `ntpath` so they run on any OS.

These do NOT prove behaviour on a real Windows machine (drive enumeration, SMB, ACLs); see docs/WINDOWS_ACCEPTANCE_CHECKLIST.md.
"""
import ntpath

import pytest

from mediacenter.paths import PathError, is_within, normalize_user_path, parent_dir


@pytest.mark.parametrize("raw,expected", [
    (r"D:\Movies", r"D:\Movies"),
    (r"D:\Movies\\", r"D:\Movies"),
    ("D:/Movies/Kids", r"D:\Movies\Kids"),
    ("D:", "D:\\"),
    ("z:\\", "z:\\"),
    (r'"E:\TV Shows"', r"E:\TV Shows"),
    (r"  C:\Users\Me\Videos  ", r"C:\Users\Me\Videos"),
    (r"\\NAS\Media", r"\\NAS\Media"),
    (r"\\nas.local\media\Movies\..\TV", r"\\nas.local\media\TV"),
    ("//NAS/Media/Movies", r"\\NAS\Media\Movies"),
    (r"\\192.168.1.5\share", r"\\192.168.1.5\share"),
    (r"\\?\D:\Very\Long\Path", r"\\?\D:\Very\Long\Path"),
])
def test_accepts_windows_paths(raw, expected):
    assert normalize_user_path(raw, ntpath) == expected


@pytest.mark.parametrize("raw", [
    "", "   ", "Movies", r"Movies\Kids", r"C:Movies", r"\Movies", r"\\NAS", r"\\NAS\\", "D:\x00evil",
])
def test_rejects_ambiguous_or_relative_windows_paths(raw):
    with pytest.raises(PathError):
        normalize_user_path(raw, ntpath)


@pytest.mark.parametrize("path,parent", [
    ("D:\\", None),
    (r"D:\Movies", "D:\\"),
    (r"D:\Movies\Kids", r"D:\Movies"),
    (r"\\NAS\Media", None),
    (r"\\NAS\Media\TV", "\\\\NAS\\Media\\"),
])
def test_parent_dir_windows(path, parent):
    assert parent_dir(path, ntpath) == parent


def key(p):
    return ntpath.normcase(ntpath.normpath(p))


@pytest.mark.parametrize("root,path,inside", [
    (r"D:\Movies", r"D:\Movies\A (2020)\a.mkv", True),
    (r"D:\Movies", r"d:\movies\A.MKV", True),                 # case-insensitive
    (r"D:\Movies", r"D:\Movies2\a.mkv", False),               # sibling with common prefix
    (r"D:\Movies", r"D:\Movies\..\Secret\a.mkv", False),      # traversal
    (r"D:\Movies", r"E:\Movies\a.mkv", False),                # other drive (ValueError handled)
    (r"\\NAS\Media", r"\\nas\media\TV\x.mp4", True),
    (r"\\NAS\Media", r"\\NAS\Media2\x.mp4", False),
    (r"\\NAS\Media", r"\\OTHER\Media\x.mp4", False),
    (r"\\NAS\Media", r"D:\x.mp4", False),
])
def test_is_within_windows(root, path, inside):
    assert is_within(key(root), key(path), ntpath) is inside


def test_posix_rules_unchanged():
    import posixpath
    assert normalize_user_path("/mnt/media/", posixpath) == "/mnt/media"
    assert parent_dir("/", posixpath) is None
    assert parent_dir("/mnt/media", posixpath) == "/mnt"
    with pytest.raises(PathError):
        normalize_user_path("media", posixpath)


class FakeStat:
    def __init__(self, attrs=0, tag=0, mode=0o040755):
        self.st_mode, self.st_file_attributes, self.st_reparse_tag = mode, attrs, tag


@pytest.mark.parametrize("attrs,tag,expected", [
    (0x10, 0, False),                       # plain NTFS directory
    (0x10 | 0x400, 0xA0000003, True),        # junction / mount point
    (0x10 | 0x400, 0xA000000C, True),        # directory symlink
    (0x10 | 0x400, 0x9000001A, False),       # OneDrive / cloud-files placeholder -> scanned normally
])
def test_windows_reparse_point_classification(monkeypatch, attrs, tag, expected):
    import mediacenter.paths as paths_mod
    monkeypatch.setattr(paths_mod.os, "lstat", lambda p: FakeStat(attrs, tag))
    assert paths_mod.is_link_or_junction(r"D:\Movies\x") is expected
