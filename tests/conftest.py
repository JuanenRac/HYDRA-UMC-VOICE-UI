# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/conftest.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The confirmation tests use "stop" as the action to confirm, so they run with the (non-default) setting that asks to confirm a stop.

tests/test_stop_setting.py removes the variable and checks the default.
"""
import pytest


@pytest.fixture(autouse=True)
def _stop_confirmation_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYDRA_UMC_VOICE_UI_STOP_REQUIRES_CONFIRMATION", "1")


@pytest.fixture(autouse=True)
def _audit_log_in_a_temporary_folder(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    """The audit log is on by default, so a server built without an explicit file must not write to the default system folder."""
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
