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
| `tests/test_cli.py` | 5, 96 | `from oathwave import ...`, `from oathwave.store import ...` |
| `tests/test_colors.py` | 3, 4 | `from oathwave import cli`, `from oathwave.colors import ...` |
| `tests/test_store.py` | 5 | `from oathwave.store import ...` |

### Docs
| File | Line(s) | What |
|---|---|---|
| `README.md` | 1, 8, 27, 33–41, 52, 56–57, 60, 76, 98–101 | title (display name `Oathwave`), prose, command examples, `OATHWAVE_FILE`, layout paths |
| `RENAME.md` | throughout | this file |

### Derived (changes automatically with `NAME`, but update the docs)
- Environment variable `OATHWAVE_FILE` (`src/oathwave/store.py`, `FILE_ENV_VAR`).

### Not the project name
- `OATHS.txt`, `Oath`, `OathFile`, `OathError`, and the word "oath" are domain
  terms, not the project name. Leave them unless you're rebranding the concept too.
- `LICENSE` and `.github/workflows/ci.yml` don't contain the name.

## Quick rename recipe

```sh
NEW=newname
git mv src/oathwave src/$NEW
grep -rl oathwave --exclude-dir=.git . | xargs sed -i "s/oathwave/$NEW/g; s/OATHWAVE/$(echo $NEW | tr a-z A-Z)/g"
python3 -m pytest -q
```
