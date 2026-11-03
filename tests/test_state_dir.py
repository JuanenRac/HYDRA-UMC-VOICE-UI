# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_state_dir.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The folder of the state files (audit log, keys, speaker store): the Linux default is kept, elsewhere it is a folder of the user, and the
tests never write outside their own temporary folder."""
import sys
from pathlib import Path

import pytest

from hydra_umc_voice_ui import voice_config
from hydra_umc_voice_ui.audit import AuditLog
from hydra_umc_voice_ui.voice_config import AuditConfig, STATE_DIR_ENV, default_state_dir, parse_voice_config


def test_the_environment_names_the_folder_and_wins_over_the_file(tmp_path: Path) -> None:
    assert default_state_dir({STATE_DIR_ENV: str(tmp_path)}) == str(tmp_path)
    config = parse_voice_config({"stateDir": str(tmp_path / "from-file")})
    assert Path(config.audit.file).parent == tmp_path / "state"  # the autouse fixture sets the variable


def test_the_file_names_the_folder_when_the_variable_is_not_set(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(STATE_DIR_ENV, raising=False)
    config = parse_voice_config({"stateDir": str(tmp_path / "from-file")})
    assert Path(config.audit.file) == tmp_path / "from-file" / "voice-ui-audit.jsonl"
    assert Path(config.speaker.store_file) == tmp_path / "from-file" / "voice-ui-speakers.json"
    assert config.state_dir == str(tmp_path / "from-file")


def test_linux_keeps_var_lib_and_other_systems_use_a_user_folder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(STATE_DIR_ENV, raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    assert default_state_dir() == "/var/lib/hydra-umc"
    assert AuditConfig().file == "/var/lib/hydra-umc/voice-ui-audit.jsonl"
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert default_state_dir() == str(tmp_path / "hydra-umc")
    assert not default_state_dir().replace("\\", "/").startswith(("C:/var", "/var"))


def test_a_run_creates_nothing_under_the_system_folders(tmp_path: Path, session_start: float) -> None:
    from conftest import touched_since

    log = AuditLog(AuditConfig())
    assert log.path.resolve().is_relative_to(tmp_path.resolve())
    assert voice_config.default_state_dir().startswith(str(tmp_path))
    assert touched_since(session_start) == []
