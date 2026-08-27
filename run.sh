#!/usr/bin/env bash
# =============================================================================
# HYDRA-UMC-VOICE-UI - run.sh
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
# Runs HYDRA-UMC-VOICE-UI's entry point. Run ./build.sh first. Forwards
# all arguments (e.g. "./run.sh analyze-audio recordings/command.wav").
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
elif [ -f .venv/Scripts/activate ]; then
    # shellcheck disable=SC1091
    source .venv/Scripts/activate
fi

python -m hydra_umc_voice_ui.main "$@"
