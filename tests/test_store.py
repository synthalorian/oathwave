import datetime as dt
import os
from pathlib import Path

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


# --- oath text must fit on one line -----------------------------------------

TODAY = dt.date(2026, 10, 29)


@pytest.mark.parametrize("text", ["", " ", "   \t  "])
def test_oath_rejects_blank_text(text):
    with pytest.raises(OathError, match="can't be empty"):
        Oath("OPEN", TODAY, None, text)


@pytest.mark.parametrize(
    "text", ["two\nlines", "carriage\rreturn", "crlf\r\n", "\nleading", "vt\vff\f", "sep\u2028x", "nel\x85x"]
)
def test_oath_rejects_line_breaks(text):
    with pytest.raises(OathError, match="newlines or carriage returns"):
        Oath("OPEN", TODAY, None, text)


def test_oath_strips_surrounding_whitespace():
    assert Oath("OPEN", TODAY, None, "  ship it \t").text == "ship it"


def test_oath_rejects_unknown_status():
    with pytest.raises(OathError, match="unknown status"):
        Oath("MAYBE", TODAY, None, "x")


def test_save_refuses_text_mutated_into_multiple_lines(oath_file):
    book = OathFile(oath_file)
    oath = Oath("OPEN", TODAY, None, "fine")
    book.add(oath)
    oath.text = "not\nfine"
    with pytest.raises(OathError, match="newlines"):
        book.save()
    assert not oath_file.exists()


# --- file access problems become OathError, not tracebacks -------------------

skip_if_root = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores file permissions"
)


def test_load_directory_path(tmp_path):
    with pytest.raises(OathError, match="it's a directory"):
        OathFile(tmp_path)


def test_save_directory_path(oath_file):
    book = OathFile(oath_file)
    book.add(Oath("OPEN", TODAY, None, "x"))
    oath_file.mkdir()  # something replaced the file with a directory meanwhile
    with pytest.raises(OathError, match="it's a directory"):
        book.save()


def test_save_missing_parent_dir(tmp_path):
    book = OathFile(tmp_path / "nope" / "OATHS.txt")  # loading a missing file is fine
    book.add(Oath("OPEN", TODAY, None, "x"))
    with pytest.raises(OathError, match="doesn't exist"):
        book.save()


def test_load_parent_is_a_file(tmp_path):
    (tmp_path / "plain").write_text("")
    with pytest.raises(OathError, match="part of the path is a file"):
        OathFile(tmp_path / "plain" / "OATHS.txt")


@skip_if_root
def test_load_unreadable_file(oath_file):
    oath_file.write_text("OPEN 2026-10-01 due:- x\n")
    oath_file.chmod(0o200)
    try:
        with pytest.raises(OathError, match="can't read .*permission denied"):
            OathFile(oath_file)
    finally:
        oath_file.chmod(0o600)


@skip_if_root
def test_save_read_only_file(oath_file):
    oath_file.write_text("OPEN 2026-10-01 due:- x\n")
    oath_file.chmod(0o400)
    try:
        book = OathFile(oath_file)
        with pytest.raises(OathError, match="can't write .*permission denied"):
            book.save()
    finally:
        oath_file.chmod(0o600)


def test_permission_error_even_as_root(oath_file, monkeypatch):
    # Same path as above, simulated, so it is covered when tests run as root.
    def deny(*args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "read_text", deny)
    with pytest.raises(OathError, match="permission denied"):
        OathFile(oath_file)


def test_load_non_utf8_file(oath_file):
    oath_file.write_bytes(b"\xff\xfe\x00garbage")
    with pytest.raises(OathError, match="not a UTF-8 text file"):
        OathFile(oath_file)
