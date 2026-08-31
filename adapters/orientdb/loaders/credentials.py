"""Read OrientDB credentials without placing secrets in source or argv."""

from __future__ import annotations

import os
import re


_SAFE_CONSOLE_TOKEN = re.compile(r"^[A-Za-z0-9_.@%+=:,!#$^&*?-]+$")


def orientdb_credentials() -> tuple[str, str]:
    username = os.environ.get("ORIENTDB_USERNAME", "").strip()
    password = os.environ.get("ORIENTDB_PASSWORD", "")
    if not username or not password:
        raise RuntimeError(
            "ORIENTDB_USERNAME and ORIENTDB_PASSWORD must be set in the process environment"
        )
    if not _SAFE_CONSOLE_TOKEN.fullmatch(username):
        raise RuntimeError("ORIENTDB_USERNAME contains unsupported console characters")
    if not _SAFE_CONSOLE_TOKEN.fullmatch(password):
        raise RuntimeError("ORIENTDB_PASSWORD contains unsupported console characters")
    return username, password


def redact_orientdb_password(text: str, password: str) -> str:
    return text.replace(password, "<redacted>") if password else text
