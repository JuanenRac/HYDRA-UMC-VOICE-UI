# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/conftest.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The confirmation tests use "stop" as the action to confirm, so they run with the (non-default) setting that asks to confirm a stop.

tests/test_stop_setting.py removes the variable and checks the default.
"""
import time
from pathlib import Path

import pytest

SYSTEM_STATE_FOLDERS = (Path("C:/var"), Path("/var/lib/hydra-umc"))


def touched_since(start: float) -> list[Path]:
    """Files under the system state folders made or changed after `start` (a run of the tests must leave none)."""
    found: list[Path] = []
    for folder in SYSTEM_STATE_FOLDERS:
        try:
            found += [p for p in folder.rglob("*") if p.is_file() and p.stat().st_mtime >= start]
        except OSError:
            continue
    return found


@pytest.fixture(scope="session", autouse=True)
def session_start():
    start = time.time() - 1
    yield start
    assert touched_since(start) == [], "the tests wrote under a system state folder: " + ", ".join(map(str, touched_since(start)))


@pytest.fixture(autouse=True)
def _stop_confirmation_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYDRA_UMC_VOICE_UI_STOP_REQUIRES_CONFIRMATION", "1")


@pytest.fixture(autouse=True)
def _audit_log_in_a_temporary_folder(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    """The audit log is on by default, so a server built without an explicit file must not write to the default system folder."""
    monkeypatch.setenv("HYDRA_UMC_VOICE_UI_STATE_DIR", str(tmp_path / "state"))
    from hydra_umc_voice_ui import http_service
    from hydra_umc_voice_ui.audit import AuditLog
    from hydra_umc_voice_ui.voice_config import AuditConfig

    default_file = AuditConfig().file

    class _TestAuditLog(AuditLog):
        def __init__(self, config: AuditConfig) -> None:
            if config.file == default_file:
                config = AuditConfig(**{**config.__dict__, "file": str(tmp_path / "default-audit.jsonl")})
            super().__init__(config)

    monkeypatch.setattr(http_service, "AuditLog", _TestAuditLog)
