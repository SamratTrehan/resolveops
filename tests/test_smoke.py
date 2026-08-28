"""Environment smoke test for the Phase 0 foundation."""

import sys


def test_python_312() -> None:
    assert sys.version_info[:2] == (3, 12)
