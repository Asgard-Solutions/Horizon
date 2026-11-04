"""Launcher configuration precedence, without starting a live server."""
import sys

import pytest

import run as launcher


@pytest.mark.parametrize("cli,environment_port,expected", [
    ([], None, 9123),
    (["--port", "9234"], None, 9234),
    ([], "9345", 9345),
])
def test_launcher_loads_env_before_port_default(tmp_path, monkeypatch, cli, environment_port, expected):
    (tmp_path / ".env").write_text("MC_PORT=9123\n", encoding="utf-8")
    monkeypatch.setattr(launcher, "BACKEND_DIR", tmp_path)
    monkeypatch.delenv("MC_PORT", raising=False)
    if environment_port is not None:
        monkeypatch.setenv("MC_PORT", environment_port)
    # Restore even values the real .env loader adds to the process environment.
    monkeypatch.setenv("MC_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(sys, "argv", ["run.py", "--check", *cli])
    checked_ports = []
    monkeypatch.setattr(launcher, "run_checks", lambda port: checked_ports.append(port) or True)
    with pytest.raises(SystemExit) as result:
        launcher.main()
    assert result.value.code == 0
    assert checked_ports == [expected]
