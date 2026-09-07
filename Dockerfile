# =============================================================================
# HYDRA-UMC-VOICE-UI - Container Build: Dockerfile
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
# Real, minimal image for the authenticated Speech-to-Action HTTP gateway
# (http_service.py's own gateway, stdlib http.server - pyproject.toml's
# own dependencies is deliberately []). Same --host/--port CLI the real
# CM5 systemd unit (systemd/hydra-umc-voice-ui.service) already runs,
# just bound to 0.0.0.0 instead of 127.0.0.1 here - a container's own
# network namespace already isolates it the way the systemd unit's
# loopback bind does on bare metal, and 127.0.0.1 inside a container
# would be unreachable from HYDRA-UMC-COGNITIVE-NODE's own container
# over the compose network. Non-root, matching that same unit's own
# User=hydra-umc-voice-ui. Consumed by HYDRA-UMC-COGNITIVE-NODE's own
# docker-compose.yml as the "voice-ui" service.
#
# IMPORTANT: binding beyond loopback requires a real bearer token
# (http_service.py's own open_gateway() raises ValueError otherwise, by
# design - the same fail-closed gate the systemd unit is also subject
# to). This image does NOT bake one in - pass a real secret at run time:
#   docker run -e HYDRA_UMC_VOICE_UI_TOKEN=... hydra-umc-voice-ui:1.0.0
# The container will refuse to start without it, exactly as intended.

FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE.md ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN useradd --system --create-home --home-dir /home/hydra hydra
USER hydra

EXPOSE 8091
ENTRYPOINT ["hydra-umc-voice-ui"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8091"]
