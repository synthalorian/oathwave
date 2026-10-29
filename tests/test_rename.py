"""Run the RENAME.md quick recipe against a scratch copy of the repo."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from oathwave import NAME

ROOT = Path(__file__).resolve().parent.parent
NEW = "vowkeeper"
SPELLINGS = (NAME, NAME.capitalize(), NAME.upper())


def gnu_sed_available():
    try:
        proc = subprocess.run(["sed", "--version"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0 and "GNU" in proc.stdout


pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("sh") is None or not gnu_sed_available(),
    reason="recipe needs sh, git and GNU sed",
)


def recipe_script():
    text = (ROOT / "RENAME.md").read_text(encoding="utf-8")
    section = text.split("## Quick rename recipe", 1)[1]
    script = re.search(r"```sh\n(.*?)```", section, re.S).group(1)
    assert "NEW=newname" in script
    # Pick our own name, and leave running the suite to the assertions below.
    script = script.replace("NEW=newname", f"NEW={NEW}")
    return "\n".join(l for l in script.splitlines() if not l.startswith("python3 -m pytest"))


def test_recipe_documents_every_spelling():
    script = recipe_script()
    for spelling in SPELLINGS:
        assert f"s/{spelling}/" in script, spelling


def test_recipe_renames_every_spelling(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(
        ROOT, repo,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.egg-info", "build", "dist"),
    )
    git = ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid"]
    subprocess.run([*git, "init", "-q"], cwd=repo, check=True, timeout=30)
    subprocess.run([*git, "add", "-A"], cwd=repo, check=True, timeout=30)

    proc = subprocess.run(["sh", "-ec", recipe_script()], cwd=repo, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert "no stragglers" in proc.stdout

    # No spelling of the old name survives, in contents or in paths.
    for path in repo.rglob("*"):
        if ".git" in path.relative_to(repo).parts:
            continue
        assert NAME not in path.name.lower(), path
        if path.is_file():
            assert NAME not in path.read_text(encoding="utf-8").lower(), path

    assert f'NAME = "{NEW}"' in (repo / "src" / NEW / "__init__.py").read_text()
    readme = (repo / "README.md").read_text()
    assert readme.startswith(f"# {NEW.capitalize()}\n")
    assert f"{NEW.upper()}_FILE" in readme
    assert f'name = "{NEW}"' in (repo / "pyproject.toml").read_text()

    # The renamed project still works.
    env = {**os.environ, "PYTHONPATH": str(repo / "src")}
    env.pop(f"{NAME.upper()}_FILE", None)
    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "tests/test_cli.py", "tests/test_store.py", "tests/test_colors.py"],
        cwd=repo, capture_output=True, text=True, env=env, timeout=120,
    )
    assert tests.returncode == 0, tests.stdout + tests.stderr
    version = subprocess.run(
        [sys.executable, "-m", NEW, "--version"], cwd=repo, capture_output=True, text=True, env=env, timeout=30,
    )
    assert version.stdout.strip().startswith(NEW)
