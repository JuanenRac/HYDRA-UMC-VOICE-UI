# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/__init__.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""HYDRA-UMC-VOICE-UI - Local Speech-to-Action pipeline (Hailo-10).

Hardware-accelerated STT/TTS with an NLU intent parser for hands-free
robotic mission control. Child of HYDRA-UMC-COGNITIVE-NODE in the
Cognitive AI Node category.
"""

# Single source of truth for the package version - mirrored into
# pyproject.toml's own `version =` field by bump_version.py on every real
# build, so main.py can print a version even if the package was never
# installed (e.g. run straight from src/).
__version__ = "0.0.5"