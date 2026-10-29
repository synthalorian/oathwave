# Oathwave

> **Swear it in plain text. Keep it or break it.**

The sun is setting over a magenta grid. You told yourself you'd ship the
landing page by Friday. You told yourself a lot of things.

`oathwave` is a tiny CLI commitment tracker for solo devs. Every promise you
make goes into one human-editable text file, `OATHS.txt`, with the day you
swore it, the day it's due, and whether you kept it. No database. No account.
No cloud. Just you, your terminal, and a neon record of your word.

- **Plain text forever** — open `OATHS.txt` in any editor, grep it, diff it, commit it.
- **Five commands** — `add`, `list`, `done`, `break`, `overdue`.
- **Zero dependencies** — pure Python standard library, 3.10+.
- **Honest** — broken oaths stay on the record. That's the point.

## Install

```sh
pip install .
```

Or run straight from a checkout without installing:

```sh
PYTHONPATH=src python3 -m oathwave --help
```

## Usage

```sh
oathwave add ship the landing page --due 2026-11-06   # absolute date
oathwave add write release notes --due +3d             # relative: +Nd days, +Nw weeks
oathwave add refactor the parser                        # no due date

oathwave list           # open oaths
oathwave list --all     # include kept and broken ones
oathwave done 1         # oath #1 kept
oathwave break 3        # oath #3 broken — it stays on the record
oathwave overdue        # open oaths past due; exits 1 if any exist
```

Oaths are numbered by their position in the file (1, 2, 3...), counting only
oath lines. `overdue` exits with status `1` when something is overdue, so you
can wire it into a shell prompt or a pre-commit hook as a guilt engine.

Errors (bad date, unknown number, malformed line) exit with status `2`.

### Choosing the file

By default `oathwave` reads and writes `./OATHS.txt` in the current directory.
Override it with:

```sh
oathwave --file ~/notes/OATHS.txt list
export OATHWAVE_FILE=~/notes/OATHS.txt
```

`--file` wins over `OATHWAVE_FILE`, which wins over the default.

### The file format

One oath per line: `STATUS  CREATED  due:DATE  text`. Separate fields with any
whitespace. `STATUS` is `OPEN`, `DONE`, or `BROKEN` (case-insensitive when
read). Use `due:-` for no due date. Blank lines and lines starting with `#`
are kept as-is.

```text
# Q4 oaths. no excuses.
OPEN    2026-10-29  due:2026-11-06  ship the landing page
DONE    2026-10-20  due:-           write the changelog
BROKEN  2026-10-01  due:2026-10-15  learn rust in two weeks
```

Edit it by hand whenever you like — `oathwave` will pick it up. When it rewrites
the file, it realigns the columns and keeps your comments.

### Color

Output glows in cyan and magenta on black. Color turns off automatically when
stdout isn't a TTY (pipes, redirects, CI), and whenever the
[`NO_COLOR`](https://no-color.org) environment variable is set to a non-empty value.

## Development

```sh
python3 -m pytest -q
```

That's it — `pyproject.toml` puts `src/` on pytest's path, so no install is
needed. The only dev dependency is `pytest`. Tests use temporary directories
and never touch your real `OATHS.txt` or the network.

Layout:

```text
src/oathwave/__init__.py   project NAME constant + version
src/oathwave/cli.py        argparse commands
src/oathwave/store.py      OATHS.txt parsing and writing
src/oathwave/colors.py     the ONLY place ANSI codes live
tests/                    pytest suite
```

Renaming the project? See [RENAME.md](RENAME.md).

## License

MIT — see [LICENSE](LICENSE).
