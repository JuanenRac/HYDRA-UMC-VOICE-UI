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
