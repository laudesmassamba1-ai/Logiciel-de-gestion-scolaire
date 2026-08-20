import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.pages.helpers import _appreciation, _parse_money


class TestAppreciation:
    def test_excellent(self):
        assert _appreciation(16) == "Excellent"
        assert _appreciation(20) == "Excellent"

    def test_tres_bien(self):
        assert _appreciation(14) == "Tres bien"
        assert _appreciation(15.9) == "Tres bien"

    def test_bien(self):
        assert _appreciation(12) == "Bien"
        assert _appreciation(13.9) == "Bien"

    def test_assez_bien(self):
        assert _appreciation(10) == "Assez bien"
        assert _appreciation(11.9) == "Assez bien"

    def test_passable(self):
        assert _appreciation(8) == "Passable"
        assert _appreciation(9.9) == "Passable"

    def test_insuffisant(self):
        assert _appreciation(0) == "Insuffisant"
        assert _appreciation(7.9) == "Insuffisant"


class TestParseMoney:
    def test_integer(self):
        assert _parse_money("25000") == 25000.0

    def test_with_suffix(self):
        assert _parse_money("25000 FCFA") == 25000.0

    def test_with_spaces(self):
        assert _parse_money("25 000") == 25000.0

    def test_comma_thousands(self):
        assert _parse_money("25 000") == 25000.0

    def test_empty_string(self):
        assert _parse_money("") == 0.0

    def test_none(self):
        assert _parse_money(None) == 0.0

    def test_zero(self):
        assert _parse_money("0") == 0.0
