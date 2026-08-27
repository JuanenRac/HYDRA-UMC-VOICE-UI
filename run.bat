@echo off
REM =============================================================================
REM HYDRA-UMC-VOICE-UI - run.bat
REM Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
REM GPL-3.0 - see LICENSE
REM =============================================================================
REM Runs HYDRA-UMC-VOICE-UI's entry point. Run build.bat first. Forwards
REM all arguments (e.g. "run.bat analyze-audio recordings\command.wav").
cd /d "%~dp0"

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

python -m hydra_umc_voice_ui.main %*
pause
