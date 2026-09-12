from pathlib import Path

import pytest

from app.context import ReviewContext
from app.tools import _safe_path


def test_safe_path_rejects_escape(tmp_path: Path):
    with pytest.raises(ValueError):
        _safe_path(tmp_path, "../outside.py")


def test_safe_path_accepts_python_file(tmp_path: Path):
    source = tmp_path / "example.py"
    source.write_text("print('ok')", encoding="utf-8")
    assert _safe_path(tmp_path, "example.py") == source.resolve()
