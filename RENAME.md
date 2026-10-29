# Renaming the project

The CLI/package name `oathwave` (display name "Oathwave") comes, at runtime, from exactly one
constant:

```python
# src/oathwave/__init__.py
NAME = "oathwave"
```

Everything the CLI prints (`prog` in `--help`, `--version`, error prefixes) and
the file environment variable (`OATHWAVE_FILE`, built as `f"{NAME.upper()}_FILE"`)
are derived from `NAME`. Packaging and imports can't read a Python constant, so
the name is also spelled out in the places below.

## Every place the name appears

Verified with:

```sh
grep -rn -i oathwave --exclude-dir=.git --exclude-dir=.pytest_cache --exclude-dir=__pycache__ .
find . -path ./.git -prune -o -iname '*oathwave*' -print
```

### Source of truth
| File | Line(s) | What |
|---|---|---|
| `src/oathwave/__init__.py` | 4 | `NAME = "oathwave"` |

### Package directory (rename the folder)
| Path | What |
|---|---|
| `src/oathwave/` | import package directory |

### Packaging
| File | Line(s) | What |
|---|---|---|
| `pyproject.toml` | 6 | `[project] name = "oathwave"` |
| `pyproject.toml` | 18 | `[project.scripts] oathwave = "oathwave.cli:main"` (script name + import path) |

### Test imports
| File | Line(s) | What |
|---|---|---|
| `tests/conftest.py` | 11 | `from oathwave.store import FILE_ENV_VAR` |
| `tests/test_cli.py` | 10, 101 | `from oathwave import ...`, `from oathwave.store import ...` |
| `tests/test_colors.py` | 3, 4 | `from oathwave import cli`, `from oathwave.colors import ...` |
| `tests/test_store.py` | 7 | `from oathwave.store import ...` |
| `tests/test_rename.py` | 12 | `from oathwave import NAME` (the test exercises the recipe below) |

### Docs
| File | Line(s) | What |
|---|---|---|
| `README.md` | 1, 8, 27, 33–41, 54, 58–59, 62, 78, 100–103 | title (display name `Oathwave`), prose, command examples, `OATHWAVE_FILE`, layout paths |
| `RENAME.md` | throughout | this file |

### Derived (changes automatically with `NAME`, but update the docs)
- Environment variable `OATHWAVE_FILE` (`src/oathwave/store.py`, `FILE_ENV_VAR`).

### Not the project name
- `OATHS.txt`, `Oath`, `OathFile`, `OathError`, and the word "oath" are domain
  terms, not the project name. Leave them unless you're rebranding the concept too.
- `LICENSE` and `.github/workflows/ci.yml` don't contain the name.

## Quick rename recipe

The name appears in three spellings — `oathwave` (package, CLI, imports),
`Oathwave` (display name in docs), and `OATHWAVE` (the `OATHWAVE_FILE` env
var) — and the recipe rewrites all three. `NEW` must be a lowercase Python
identifier (letters, digits, underscores; not starting with a digit).

```sh
NEW=newname
NEW_TITLE=$(printf '%s' "$NEW" | awk '{ print toupper(substr($0, 1, 1)) substr($0, 2) }')
NEW_UPPER=$(printf '%s' "$NEW" | tr '[:lower:]' '[:upper:]')
git mv src/oathwave "src/$NEW"
grep -rli oathwave --exclude-dir=.git --exclude-dir=.pytest_cache --exclude-dir=__pycache__ . \
  | xargs sed -i "s/oathwave/$NEW/g; s/Oathwave/$NEW_TITLE/g; s/OATHWAVE/$NEW_UPPER/g"
grep -rni oathwave --exclude-dir=.git --exclude-dir=.pytest_cache --exclude-dir=__pycache__ . \
  || echo "no stragglers"
python3 -m pytest -q
```

`grep -i` finds files containing *any* spelling (a plain `grep oathwave` would
miss a file that only says `Oathwave` or `OATHWAVE`), and the second grep
reports any mixed-case spelling the three substitutions didn't cover. The
`sed -i` form is GNU sed; on macOS use `sed -i ''`.
