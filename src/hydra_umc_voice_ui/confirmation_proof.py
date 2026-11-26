# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/confirmation_proof.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The `ConfirmationProof` of HYDRA-UMC-SDK (hydra_umc_sdk.confirmation_proof), the same bytes, kept here because this service installs no dependency.

`subject_id` is the machine the action is for (the robot id; the id of the installation when a spoken command names none) and `action_id` the trajectory
fingerprint or the spoken request id; a name that does not fit the identifier pattern becomes `proof_identifier` of it. The signature is HMAC-SHA256 over
length-prefixed parts with the key of the `kind`: a file of one line of at least 32 characters, mode 600, shared only with the layer that acts.
"""

from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

KINDS = ("approval", "voice")
MAX_PROOF_VALIDITY_MS = 3_600_000
FUTURE_TOLERANCE_MS = 5_000
MIN_KEY_BYTES = 32
_TAG = "hydra-umc-confirmation-proof-v1"
_IDENTIFIER = re.compile(r"[A-Za-z0-9._:-]{1,64}")
_APPROVAL_ID = re.compile(r"[0-9a-f]{32}")
_SIGNATURE = re.compile(r"[0-9a-f]{64}")
_REQUIRED = {"schema_version", "kind", "action_id", "subject_id", "operator", "approved_at_ms", "expires_at_ms", "signature"}


def proof_identifier(text: str) -> str:
    """`text` when it fits the identifier of a proof, else `sha256:` and the first 57 hexadecimal digits of its SHA-256."""
    if not text:
        raise ValueError("an identifier of a proof cannot be empty")
    return text if _IDENTIFIER.fullmatch(text) else "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:57]


def load_proof_key(path: str) -> bytes:
    """The key in `path`; ValueError (never naming the key) when it cannot be used."""
    try:
        info = os.stat(path)
        with open(path, "rb") as handle:
            raw = handle.read(4096)
    except OSError as error:
        raise ValueError(f"the confirmation key file cannot be read: {type(error).__name__}") from error
    if os.name == "posix" and info.st_mode & 0o077:
        raise ValueError("the confirmation key file must not be readable by the group or by others (mode 600)")
    key = raw.strip()
    if len(key) < MIN_KEY_BYTES:
        raise ValueError(f"the confirmation key must have at least {MIN_KEY_BYTES} characters")
    return key


def _message(proof: dict[str, Any]) -> bytes:
    parts = (_TAG, proof["kind"], proof["action_id"], proof["subject_id"], proof["operator"], str(proof["approved_at_ms"]), str(proof["expires_at_ms"]), proof.get("approval_id", ""))
    out = b""
    for part in parts:
        raw = part.encode("utf-8")
        out += str(len(raw)).encode("ascii") + b":" + raw
    return out


def _well_formed(proof: Any) -> bool:
    if not isinstance(proof, dict) or not _REQUIRED <= set(proof) <= _REQUIRED | {"approval_id"} or proof["schema_version"] != "1.0" or proof["kind"] not in KINDS:
        return False
    if not all(isinstance(proof[n], str) and _IDENTIFIER.fullmatch(proof[n]) for n in ("action_id", "subject_id", "operator")):
        return False
    if not all(type(proof[n]) is int and proof[n] >= 0 for n in ("approved_at_ms", "expires_at_ms")):
        return False
    if "approval_id" in proof and not (isinstance(proof["approval_id"], str) and _APPROVAL_ID.fullmatch(proof["approval_id"])):
        return False
    return isinstance(proof["signature"], str) and _SIGNATURE.fullmatch(proof["signature"]) is not None


def sign_proof(key: bytes, *, kind: str, action_id: str, subject_id: str, operator: str, approved_at_ms: int, expires_at_ms: int, approval_id: str) -> dict[str, Any]:
    proof: dict[str, Any] = {"schema_version": "1.0", "kind": kind, "action_id": action_id, "subject_id": subject_id, "operator": operator,
                             "approved_at_ms": approved_at_ms, "expires_at_ms": expires_at_ms, "approval_id": approval_id}
    proof["signature"] = hmac.new(key, _message(proof), hashlib.sha256).hexdigest()
    if not _well_formed(proof):
        raise ValueError("the confirmation proof would not be well formed")
    return proof


def verify_proof(key: bytes, proof: Any, *, expected_action_id: str, expected_subject_id: str, now_ms: int | None = None) -> tuple[bool, str]:
    """(True, "") only for a genuine, current proof of exactly this action and subject that carries an identity (so it can be accepted once)."""
    now = int(time.time() * 1000) if now_ms is None else now_ms
    if not _well_formed(proof):
        return False, "the proof is not a well formed confirmation"
    if not hmac.compare_digest(hmac.new(key, _message(proof), hashlib.sha256).hexdigest(), proof["signature"]):
        return False, "the signature of the proof does not match"
    if proof["action_id"] != expected_action_id:
        return False, "the proof is for a different action"
    if proof["subject_id"] != expected_subject_id:
        return False, "the proof is for a different subject"
    if proof["expires_at_ms"] <= proof["approved_at_ms"] or proof["expires_at_ms"] - proof["approved_at_ms"] > MAX_PROOF_VALIDITY_MS:
        return False, "the validity of the proof is not acceptable"
    if proof["approved_at_ms"] > now + FUTURE_TOLERANCE_MS:
        return False, "the proof was given in the future"
    if now >= proof["expires_at_ms"]:
        return False, "the proof has expired"
    if "approval_id" not in proof:
        return False, "the proof has no identity to accept it only once"
    return True, ""


# Asking HYDRA-UMC-COGNITIVE-NODE ----------------------------------------------------------------------------------------------------
# The layer that holds a confirmation asks the node whether it may be executed, with the subject and, when it signed one, the proof.
# Anything but a clear "allow" (no answer, an error, a redirect, another decision) is a refusal.

ASK_TIMEOUT_SECONDS = 3.0
UNREACHABLE = "the cognitive node could not be asked"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def check_node_url(url: str) -> str:
    """The base address of the node without a trailing slash; ValueError when it is not a plain http(s) address."""
    parts = urllib.parse.urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("the address of the cognitive node must be http://host[:port] or https://host[:port]")
    return url.strip().rstrip("/")


def load_node_token(path: str) -> str:
    """The bearer token for the node ("" without a file); ValueError when a named file cannot be used."""
    if not path:
        return ""
    try:
        token = Path(path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f"the token file of the cognitive node cannot be read: {type(error).__name__}") from error
    if len(token) < 16 or not token.isascii() or not token.isprintable():
        raise ValueError("the token of the cognitive node must have at least 16 printable characters")
    return token


def ask_autonomy(url: str, token: str, *, source: str, kind: str, action_id: str, subject_id: str, proof: dict[str, Any] | None,
                 timeout: float = ASK_TIMEOUT_SECONDS) -> tuple[bool, str]:
    """(True, "") only when the node allows `execute_with_confirmation` for this action and subject; else (False, why)."""
    question: dict[str, Any] = {"source": source, "kind": kind, "actionId": action_id, "level": "execute_with_confirmation",
                                "humanConfirmed": True, "subjectId": subject_id}
    if proof is not None:
        question["confirmationProof"] = proof
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        request = urllib.request.Request(check_node_url(url) + "/autonomy/evaluate", data=json.dumps(question).encode("utf-8"), headers=headers, method="POST")
        with opener.open(request, timeout=timeout) as response:
            answer = json.loads(response.read(65536))
    except urllib.error.HTTPError as error:
        error.close()
        return False, UNREACHABLE
    except (OSError, ValueError, http.client.HTTPException):
        return False, UNREACHABLE
    if not isinstance(answer, dict):
        return False, UNREACHABLE
    if answer.get("decision") == "allow":
        return True, ""
    reason = answer.get("reason")
    shown = reason if isinstance(reason, str) and re.fullmatch(r"[a-z_]{1,64}", reason) else "no reason given"
    return False, f"the autonomy policy did not allow it ({shown})"
