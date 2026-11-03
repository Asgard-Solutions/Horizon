import shutil
import subprocess

import pytest

from mediacenter.probe import assess_playback, probe_file

H264_AAC = {"video": [{"codec": "h264", "profile": "High", "pix_fmt": "yuv420p", "level": 40}],
            "audio": [{"codec": "aac"}]}


def test_avi_is_unsupported_without_probe():
    r = assess_playback("avi", None)
    assert r["status"] == "unsupported" and "AVI" in r["reasons"][0]


def test_mp4_h264_aac_supported():
    r = assess_playback("mp4", H264_AAC)
    assert r["status"] == "supported" and r["codecs"] == "avc1.640028, mp4a.40.2"


def test_mp4_without_probe_is_unknown():
    assert assess_playback("mp4", None)["status"] == "unknown"


def test_mkv_is_maybe():
    assert assess_playback("mkv", H264_AAC)["status"] == "maybe"


def test_mp4_mpeg4_video_unsupported():
    probe = {"video": [{"codec": "mpeg4"}], "audio": [{"codec": "mp3"}]}
    assert assess_playback("mp4", probe)["status"] == "unsupported"


def test_hevc_and_dolby_audio_are_maybe():
    assert assess_playback("mp4", {"video": [{"codec": "hevc"}], "audio": [{"codec": "aac"}]})["status"] == "maybe"
    r = assess_playback("mp4", {"video": [{"codec": "h264"}], "audio": [{"codec": "dts"}]})
    assert r["status"] == "maybe" and any("dts" in x for x in r["reasons"])


def test_10bit_h264_unsupported():
    probe = {"video": [{"codec": "h264", "pix_fmt": "yuv420p10le"}], "audio": [{"codec": "aac"}]}
    assert assess_playback("mp4", probe)["status"] == "unsupported"


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg/ffprobe not installed")
def test_real_ffprobe(tmp_path):
    out = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=24",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", str(out)], check=True)
    probe = probe_file(shutil.which("ffprobe"), str(out))
    assert probe["video"][0]["codec"] == "h264" and probe["audio"][0]["codec"] == "aac"
    assert 1.5 < probe["duration"] < 2.6
    assert assess_playback("mp4", probe)["status"] == "supported"
