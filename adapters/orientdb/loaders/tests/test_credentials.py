from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

LOADERS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LOADERS_DIR))
from credentials import orientdb_credentials, redact_orientdb_password


class OrientDBCredentialsTest(unittest.TestCase):
    def test_requires_username_and_password(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "must be set"):
                orientdb_credentials()

    def test_rejects_console_metacharacters(self) -> None:
        with patch.dict(
            os.environ,
            {"ORIENTDB_USERNAME": "admin", "ORIENTDB_PASSWORD": "bad;command"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "unsupported"):
                orientdb_credentials()

    def test_redacts_password_from_console_output(self) -> None:
        with patch.dict(
            os.environ,
            {"ORIENTDB_USERNAME": "audit", "ORIENTDB_PASSWORD": "Test-Only_42!"},
            clear=True,
        ):
            username, password = orientdb_credentials()
            output = f"connect {username} {password}"
            self.assertEqual(
                redact_orientdb_password(output, password),
                "connect audit <redacted>",
            )


if __name__ == "__main__":
    unittest.main()
