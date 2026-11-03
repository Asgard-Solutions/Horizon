import pytest

from mediacenter.parser import clean_name, is_video, parse_episode, parse_movie, season_from_dir


@pytest.mark.parametrize("name,expected", [
    ("a.mp4", True), ("a.MKV", True), ("a.avi", True), ("a.m4v", True), ("a.mov", True),
    ("a.txt", False), ("a.nfo", False), ("poster.jpg", False), (".mp4", False), ("mp4", False),
])
def test_is_video(name, expected):
    assert is_video(name) is expected


@pytest.mark.parametrize("filename,dirs,title,year", [
    ("Sample Movie (2024).mp4", [], "Sample Movie", 2024),
    ("Sample.Movie.2024.1080p.BluRay.x264.mkv", [], "Sample Movie", 2024),
    ("Another_Film_[2019].m4v", [], "Another Film", 2019),
    ("2001 A Space Odyssey (1968).mkv", [], "2001 A Space Odyssey", 1968),
    ("Blade Runner 2049 (2017).mp4", [], "Blade Runner 2049", 2017),
    ("Untitled Home Video.avi", [], "Untitled Home Video", None),
    ("Some.Movie.720p.WEB-DL.mp4", [], "Some Movie", None),
    ("movie.mp4", ["Great Film (1999)"], "Great Film", 1999),
    ("Great Film (1999).mkv", ["Great Film (1999)"], "Great Film", 1999),
])
def test_parse_movie(filename, dirs, title, year):
    info = parse_movie(filename, dirs)
    assert info == {"title": title, "year": year}


@pytest.mark.parametrize("filename,dirs,show,season,episode,ep_title", [
    ("Sample Show - S01E02.mkv", [], "Sample Show", 1, 2, None),
    ("Sample.Show.S01E02.720p.HDTV.x264.mkv", [], "Sample Show", 1, 2, None),
    ("sample show s10e110.mp4", [], "sample show", 10, 110, None),
    ("Sample Show - S02E01 - The Return.m4v", ["Sample Show", "Season 02"], "Sample Show", 2, 1, "The Return"),
    ("S01E03.mkv", ["Folder Show", "Season 1"], "Folder Show", 1, 3, None),
    ("Episode S01E04.mkv", ["Folder Show", "S01"], "Folder Show", 1, 4, None),
    ("Show 1x05 Title.avi", [], "Show", 1, 5, "Title"),
    ("Other.Series.S02E05.720p.mp4", ["Other Series (2019)", "Season 2"], "Other Series", 2, 5, None),
])
def test_parse_episode(filename, dirs, show, season, episode, ep_title):
    info = parse_episode(filename, dirs)
    assert info is not None
    assert info["show_title"] == show
    assert info["season"] == season
    assert info["episode"] == episode
    assert info["episode_title"] == ep_title


def test_parse_episode_show_year_from_folder():
    info = parse_episode("Other.Series.S02E05.mp4", ["Other Series (2019)", "Season 2"])
    assert info["show_year"] == 2019
    assert info["show_key"] == "other series|2019"


def test_multi_episode():
    info = parse_episode("Show - S01E01-E02.mkv", [])
    assert (info["episode"], info["episode_end"]) == (1, 2)


@pytest.mark.parametrize("filename", [
    "Sample Movie (2024).mp4", "1920x1080 demo.mp4", "Movie.2010.1080p.mkv", "Season Finale.mp4",
])
def test_not_episode(filename):
    assert parse_episode(filename, []) is None


def test_episode_without_show_name_at_root_is_rejected():
    assert parse_episode("S01E01.mkv", []) is None


@pytest.mark.parametrize("name,num", [("Season 1", 1), ("season_02", 2), ("S03", 3), ("Specials", None), ("Staffel 4", 4)])
def test_season_dir(name, num):
    assert season_from_dir(name) == num


def test_clean_name():
    assert clean_name("The.Big_Movie - ") == "The Big Movie"
