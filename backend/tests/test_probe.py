import shutil
import subprocess

import pytest

from mediacenter import probe as pmod
from mediacenter.durations import DurationWorker
from mediacenter.probe import assess_playback, ffprobe_version, find_ffprobe, probe_file

H264_AAC = {"video": [{"codec": "h264", "profile": "High", "pix_fmt": "yuv420p", "level": 40}],
            "audio": [{"codec": "aac"}]}


@pytest.mark.parametrize("returncode,output", [(1, "ffprobe version broken"), (0, "other program"), (0, "")])
def test_discovery_rejects_unusable_ffprobe(tmp_path, monkeypatch, returncode, output):
    binary = tmp_path / "ffprobe.exe"
    binary.write_bytes(b"fixture")
    monkeypatch.setattr(pmod, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(pmod.shutil, "which", lambda _name: None)
    monkeypatch.setattr(pmod.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a[0], returncode, output, ""))
    assert find_ffprobe(str(binary)) is None
    assert ffprobe_version(str(binary)) is None


@pytest.mark.parametrize("usable,expected", [
    ({"configured", "bundled", "path"}, "configured"),
    ({"bundled", "path"}, "bundled"),
    ({"path"}, "path"),
    (set(), None),
])
def test_discovery_uses_first_usable_candidate(tmp_path, monkeypatch, usable, expected):
    candidates = {"configured": tmp_path / "configured.exe", "bundled": tmp_path / "tools" / "ffprobe.exe",
                  "path": tmp_path / "path.exe"}
    # Match the platform-specific bundled filename.
    if pmod.os.name != "nt":
        candidates["bundled"] = tmp_path / "tools" / "ffprobe"
    for binary in candidates.values():
        binary.parent.mkdir(exist_ok=True)
        binary.write_bytes(b"fixture")

    def version_command(args, **kwargs):
        valid = any(args[0] == str(candidates[source]) for source in usable)
        return subprocess.CompletedProcess(args, 0 if valid else 1, "ffprobe version fixture" if valid else "", "")

    monkeypatch.setattr(pmod, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(pmod.shutil, "which", lambda _name: str(candidates["path"]))
    monkeypatch.setattr(pmod.subprocess, "run", version_command)
    assert find_ffprobe(str(candidates["configured"])) == (str(candidates[expected]) if expected else None)


@pytest.mark.parametrize("failure", [OSError("not executable"), subprocess.TimeoutExpired("ffprobe", 10)])
def test_discovery_rejects_launch_failures(tmp_path, monkeypatch, failure):
    binary = tmp_path / "ffprobe.exe"
    binary.write_bytes(b"fixture")

    def cannot_launch(*args, **kwargs):
        raise failure

    monkeypatch.setattr(pmod, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(pmod.shutil, "which", lambda _name: None)
    monkeypatch.setattr(pmod.subprocess, "run", cannot_launch)
    assert find_ffprobe(str(binary)) is None


def test_absent_ffprobe_does_not_launch_a_process(tmp_path, monkeypatch):
    monkeypatch.setattr(pmod, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(pmod.shutil, "which", lambda _name: None)

    def unexpected_launch(*args, **kwargs):
        pytest.fail("FFprobe absence must not launch a process")

    monkeypatch.setattr(pmod.subprocess, "run", unexpected_launch)
    assert find_ffprobe(str(tmp_path / "missing.exe")) is None
    assert ffprobe_version(None) is None


def test_discovery_caches_validation_until_executable_changes(tmp_path, monkeypatch):
    binary = tmp_path / "ffprobe.exe"
    binary.write_bytes(b"fixture")
    calls = []

    def version_command(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "ffprobe version fixture\nconfiguration: fixture\n", "")

    monkeypatch.setattr(pmod.subprocess, "run", version_command)
    for _ in range(3):
        assert find_ffprobe(str(binary)) == str(binary)
        assert ffprobe_version(str(binary)) == "ffprobe version fixture"
    assert calls == [[str(binary), "-version"]]
    binary.write_bytes(b"updated executable fixture")
    assert find_ffprobe(str(binary)) == str(binary)
    assert len(calls) == 2


@pytest.mark.parametrize("failure", [subprocess.TimeoutExpired("ffprobe", 10), OSError("temporarily unavailable")],
                         ids=["timeout", "temporary-os-error"])
def test_discovery_retries_transient_validation_failure_without_executable_change(tmp_path, monkeypatch, failure):
    binary = tmp_path / "ffprobe.exe"
    binary.write_bytes(b"fixture")
    before = binary.stat()
    calls = []

    def version_command(args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            raise failure
        return subprocess.CompletedProcess(args, 0, "ffprobe version recovered\n", "")

    monkeypatch.setattr(pmod, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(pmod.shutil, "which", lambda _name: None)
    monkeypatch.setattr(pmod.subprocess, "run", version_command)
    assert find_ffprobe(str(binary)) is None
    after = binary.stat()
    assert (after.st_mtime_ns, after.st_ctime_ns, after.st_size) == (before.st_mtime_ns, before.st_ctime_ns, before.st_size)
    assert find_ffprobe(str(binary)) == str(binary)
    assert ffprobe_version(str(binary)) == "ffprobe version recovered"
    assert find_ffprobe(str(binary)) == str(binary)
    assert calls == [[str(binary), "-version"], [str(binary), "-version"]]


def test_invalid_executable_is_unavailable_not_an_offline_source(app, host, media_root, tmp_path, monkeypatch):
    binary = tmp_path / "invalid-ffprobe.exe"
    binary.write_bytes(b"This is not an executable.")
    monkeypatch.setattr(pmod, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(pmod.shutil, "which", lambda _name: None)
    app.state.config.ffprobe_path = str(binary)
    app.state.durations = DurationWorker(app.state.config.db_path, str(binary), 2)
    assert host.post("/api/libraries", json={"path": str(media_root)}).status_code == 200
    assert app.state.durations.run_until_idle() == 0
    status = host.get("/api/metadata/status").json()
    assert status["available"] is False
    assert status["unreachable"] == 0
    assert status["pending"] == 7
    assert {movie["runtime_status"] for movie in host.get("/api/movies").json()} == {"unknown"}
    assert host.get("/api/system").json()["ffprobe"] == {"path": None, "version": None}


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
