"""Encrypted persistence for trial-key rotation state."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path

APP_STATE_DIR = "FuelCellHMIDemo"
STATE_FILENAME = "rotation_state.enc.json"
STATE_VERSION = 1
_PEPPER = "hmi-demo-rotation-v1"


def _state_path() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        base = Path(appdata) / APP_STATE_DIR
    else:
        base = Path.home() / f".{APP_STATE_DIR.lower()}"
    base.mkdir(parents=True, exist_ok=True)
    return base / STATE_FILENAME


def _derive_key(admin_key: str) -> bytes:
    seed = f"{admin_key}|{_PEPPER}".encode("utf-8")
    return hashlib.sha256(seed).digest()


def _keystream(key: bytes, nonce: bytes, size: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < size:
        blk = hashlib.sha256(key + nonce + ctr.to_bytes(4, "big")).digest()
        out.extend(blk)
        ctr += 1
    return bytes(out[:size])


def _encrypt(data: bytes, key: bytes) -> str:
    nonce = os.urandom(16)
    ks = _keystream(key, nonce, len(data))
    cipher = bytes(a ^ b for a, b in zip(data, ks))
    return base64.urlsafe_b64encode(nonce + cipher).decode("ascii")


def _decrypt(token: str, key: bytes) -> bytes:
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    if len(raw) < 17:
        raise ValueError("invalid encrypted payload")
    nonce, cipher = raw[:16], raw[16:]
    ks = _keystream(key, nonce, len(cipher))
    return bytes(a ^ b for a, b in zip(cipher, ks))


def load_rotation_state(trial_groups: list[dict], admin_key: str) -> None:
    # Safe defaults
    for grp in trial_groups:
        keys = grp.get("keys", [])
        grp["next_idx"] = int(grp.get("next_idx", 0)) % len(keys) if keys else 0

    path = _state_path()
    if not path.exists():
        return

    try:
        wrapper = json.loads(path.read_text(encoding="utf-8"))
        if int(wrapper.get("version", 0)) != STATE_VERSION:
            return
        token = wrapper.get("payload", "")
        if not token:
            return
        plain = _decrypt(token, _derive_key(admin_key))
        payload = json.loads(plain.decode("utf-8"))
        saved = payload.get("groups", {})

        for grp in trial_groups:
            gid = grp.get("id")
            keys = grp.get("keys", [])
            idx = int(saved.get(gid, 0))
            grp["next_idx"] = idx % len(keys) if keys else 0
    except Exception:
        # Corrupt/unknown file should not break app startup.
        return


def save_rotation_state(trial_groups: list[dict], admin_key: str) -> None:
    path = _state_path()
    payload = {
        "groups": {
            str(grp.get("id")): int(grp.get("next_idx", 0))
            for grp in trial_groups
            if grp.get("id") and grp.get("keys")
        }
    }
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    token = _encrypt(data, _derive_key(admin_key))
    wrapper = {"version": STATE_VERSION, "payload": token}

    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(wrapper, separators=(",", ":"), ensure_ascii=True),
        encoding="utf-8",
    )
    tmp.replace(path)
