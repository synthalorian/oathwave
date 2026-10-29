import datetime as dt
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

from oathwave import NAME, cli


def run(oath_file, *argv, today="2026-10-29"):
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(["-f", str(oath_file), "--today", today, *argv], out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_add_writes_plain_text_line(oath_file):
    code, out, _ = run(oath_file, "add", "ship", "the", "thing", "--due", "2026-11-05")
    assert code == 0
    assert "#1" in out
    assert oath_file.read_text() == "OPEN    2026-10-29  due:2026-11-05  ship the thing\n"


def test_add_relative_due(oath_file):
    run(oath_file, "add", "a", "--due", "+3d")
    run(oath_file, "add", "b", "--due", "+1w")
    text = oath_file.read_text()
    assert "due:2026-11-01" in text
    assert "due:2026-11-05" in text


def test_add_bad_due(oath_file):
    code, _, err = run(oath_file, "add", "a", "--due", "someday")
    assert code == 2
    assert "bad date" in err
    assert not oath_file.exists()


def test_list_hides_closed_unless_all(oath_file):
    run(oath_file, "add", "keep me")
    run(oath_file, "add", "finish me")
    run(oath_file, "done", "2")
    _, out, _ = run(oath_file, "list")
    assert "keep me" in out and "finish me" not in out
    _, out, _ = run(oath_file, "list", "--all")
    assert "finish me" in out and "DONE" in out


def test_list_empty(oath_file):
    code, out, _ = run(oath_file, "list")
    assert code == 0
    assert "no oaths" in out


def test_done_and_break(oath_file):
    run(oath_file, "add", "one")
    run(oath_file, "add", "two")
    assert run(oath_file, "done", "1")[0] == 0
    assert run(oath_file, "break", "2")[0] == 0
    lines = oath_file.read_text().splitlines()
    assert lines[0].startswith("DONE")
    assert lines[1].startswith("BROKEN")


def test_cannot_close_twice(oath_file):
    run(oath_file, "add", "one")
    run(oath_file, "done", "1")
    code, _, err = run(oath_file, "break", "1")
    assert code == 2
    assert "already DONE" in err


def test_unknown_number(oath_file):
    code, _, err = run(oath_file, "done", "7")
    assert code == 2
    assert f"{NAME}: error:" in err


def test_overdue(oath_file):
    run(oath_file, "add", "late", "--due", "2026-10-01")
    run(oath_file, "add", "fine", "--due", "2026-12-01")
    run(oath_file, "add", "whenever")
    code, out, _ = run(oath_file, "overdue")
    assert code == 1
    assert "late" in out and "fine" not in out and "whenever" not in out
    run(oath_file, "done", "1")
    code, out, _ = run(oath_file, "overdue")
    assert code == 0
    assert "nothing overdue" in out


def test_hand_edited_file_is_respected(oath_file):
    oath_file.write_text("# edited in vim\nOPEN 2026-10-01 due:- typed by hand\n")
    _, out, _ = run(oath_file, "list")
    assert "typed by hand" in out


def test_env_var_selects_file(monkeypatch, tmp_path):
    from oathwave.store import FILE_ENV_VAR

    target = tmp_path / "elsewhere.txt"
    monkeypatch.setenv(FILE_ENV_VAR, str(target))
    cli.main(["add", "via env"], out=io.StringIO())
    assert "via env" in target.read_text()


def test_default_file_in_cwd(tmp_path):
    cli.main(["add", "local"], out=io.StringIO())
    assert (tmp_path / "OATHS.txt").exists()


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert NAME in capsys.readouterr().out


# --- bad oath text ----------------------------------------------------------

@pytest.mark.parametrize("words", [[""], ["   "], [" ", "\t"]])
def test_add_rejects_blank_text(oath_file, words):
    code, out, err = run(oath_file, "add", *words)
    assert code == 2
    assert "can't be empty" in err and out == ""
    assert not oath_file.exists()


@pytest.mark.parametrize("text", ["line one\nline two", "sneaky\rreturn", "dos\r\nending"])
def test_add_rejects_line_breaks(oath_file, text):
    code, _, err = run(oath_file, "add", text)
    assert code == 2
    assert "newlines or carriage returns" in err
    assert not oath_file.exists()


def test_rejected_text_leaves_existing_file_loadable(oath_file):
    run(oath_file, "add", "first")
    before = oath_file.read_text()
    assert run(oath_file, "add", "evil\nOPEN 2026-01-01 due:- injected")[0] == 2
    assert oath_file.read_text() == before
    code, out, _ = run(oath_file, "list")
    assert code == 0 and "first" in out and "injected" not in out


# --- file access problems ---------------------------------------------------

def test_file_is_a_directory(tmp_path):
    code, _, err = run(tmp_path, "list")
    assert code == 2
    assert err.count("\n") == 1 and "it's a directory" in err


def test_missing_parent_dir_on_add(tmp_path):
    code, _, err = run(tmp_path / "missing" / "OATHS.txt", "add", "x")
    assert code == 2
    assert err.count("\n") == 1 and "doesn't exist" in err


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores file permissions")
def test_unreadable_file(oath_file):
    oath_file.write_text("")
    oath_file.chmod(0o000)
    try:
        code, _, err = run(oath_file, "list")
    finally:
        oath_file.chmod(0o600)
    assert code == 2
    assert err.count("\n") == 1 and "permission denied" in err


def test_file_errors_have_no_traceback_end_to_end(tmp_path):
    src = Path(__file__).resolve().parent.parent / "src"
    env = {**os.environ, "PYTHONPATH": str(src)}
    proc = subprocess.run(
        [sys.executable, "-m", NAME, "-f", str(tmp_path), "list"],
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert proc.returncode == 2
    assert "Traceback" not in proc.stderr
    assert proc.stderr.startswith(f"{NAME}: error:")


# --- relative due overflow --------------------------------------------------

@pytest.mark.parametrize("due", ["+99999999d", "+999999999999w", "+2930000d", "+" + "9" * 30 + "d"])
def test_huge_relative_due(oath_file, due):
    code, _, err = run(oath_file, "add", "eventually", "--due", due)
    assert code == 2
    assert "too far out" in err
    assert not oath_file.exists()


def test_relative_due_up_to_max_date_is_fine(oath_file):
    days = (dt.date.max - dt.date(2026, 10, 29)).days
    assert run(oath_file, "add", "eventually", "--due", f"+{days}d")[0] == 0
    assert "due:9999-12-31" in oath_file.read_text()
