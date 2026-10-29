import io

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
