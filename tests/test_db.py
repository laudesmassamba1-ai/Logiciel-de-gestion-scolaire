import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db import hash_password, verify_password


class TestHashPassword:
    def test_returns_string_with_colon(self):
        result = hash_password("test123")
        assert isinstance(result, str)
        assert ":" in result

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("test123")
        h2 = hash_password("test123")
        assert h1 != h2

    def test_hex_format(self):
        result = hash_password("test123")
        salt_hex, hash_hex = result.split(":")
        assert len(salt_hex) == 32
        assert len(hash_hex) == 64


class TestVerifyPassword:
    def test_correct_password(self):
        stored = hash_password("secret")
        assert verify_password("secret", stored) is True

    def test_wrong_password(self):
        stored = hash_password("secret")
        assert verify_password("wrong", stored) is False

    def test_empty_password(self):
        stored = hash_password("")
        assert verify_password("", stored) is True

    def test_unicode_password(self):
        stored = hash_password("mot de passe é")
        assert verify_password("mot de passe é", stored) is True
