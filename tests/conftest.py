import sys
from pathlib import Path

import pytest

# Make src/ importable without installing (belt and braces with pytest's pythonpath).
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oathwave.store import FILE_ENV_VAR  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    """Never touch a real oath file or inherit the caller's color settings."""
    monkeypatch.delenv(FILE_ENV_VAR, raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def oath_file(tmp_path):
    return tmp_path / "OATHS.txt"
