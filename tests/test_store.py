import datetime as dt

import pytest

from oathwave.store import Oath, OathError, OathFile, parse_line, resolve_path, FILE_ENV_VAR


def test_round_trip_preserves_comments(oath_file):
    oath_file.write_text(
        "# my oaths\n"
        "OPEN    2026-10-01  due:2026-10-05  ship v1\n"
        "\n"
        "done    2026-10-02  due:-           write docs\n"
    )
    book = OathFile(oath_file)
    assert [o.status for o in book.oaths] == ["OPEN", "DONE"]
    assert book.oaths[1].due is None
    book.save()
    text = oath_file.read_text()
    assert text.startswith("# my oaths\n")
    assert "\n\n" in text
    assert OathFile(oath_file).oaths == book.oaths


def test_missing_file_is_empty(oath_file):
    assert OathFile(oath_file).oaths == []


def test_bad_line_reports_line_number():
    with pytest.raises(OathError, match="line 3"):
        parse_line("garbage", 3)


def test_bad_status():
    with pytest.raises(OathError, match="unknown status"):
        parse_line("MAYBE 2026-10-01 due:- x", 1)


def test_overdue_only_when_open():
    today = dt.date(2026, 10, 10)
    past = dt.date(2026, 10, 1)
    assert Oath("OPEN", past, past, "x").is_overdue(today)
    assert not Oath("DONE", past, past, "x").is_overdue(today)
    assert not Oath("OPEN", past, None, "x").is_overdue(today)
    assert not Oath("OPEN", past, today, "x").is_overdue(today)


def test_resolve_path_env(monkeypatch, tmp_path):
    monkeypatch.setenv(FILE_ENV_VAR, str(tmp_path / "x.txt"))
    assert resolve_path() == tmp_path / "x.txt"
    assert resolve_path("y.txt").name == "y.txt"
