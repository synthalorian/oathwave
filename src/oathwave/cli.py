"""Command-line entry point."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from typing import Sequence, TextIO

from . import NAME, __version__
from .colors import Palette, palette_for
from .store import FILE_ENV_VAR, Oath, OathError, OathFile, parse_date, resolve_path


def parse_due(value: str, today: dt.date) -> dt.date:
    """Accept YYYY-MM-DD or a relative offset like +3d / +2w."""
    if value.startswith("+") and len(value) > 2 and value[-1] in "dw":
        try:
            n = int(value[1:-1])
        except ValueError:
            raise OathError(f"bad relative due {value!r} (try +3d or +2w)") from None
        try:
            return today + dt.timedelta(days=n * (7 if value[-1] == "w" else 1))
        except OverflowError:
            raise OathError(f"relative due {value!r} is too far out (dates stop at {dt.date.max})") from None
    return parse_date(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=NAME,
        description="Swear it in plain text. Keep it or break it.",
    )
    parser.add_argument("--version", action="version", version=f"{NAME} {__version__}")
    parser.add_argument(
        "-f", "--file",
        help=f"oath file (default: ${FILE_ENV_VAR} or ./OATHS.txt)",
    )
    parser.add_argument("--today", help=argparse.SUPPRESS)  # time travel, for tests
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p_add = sub.add_parser("add", help="swear a new oath")
    p_add.add_argument("text", nargs="+", help="what you promise")
    p_add.add_argument("-d", "--due", help="YYYY-MM-DD, +3d, or +2w")

    p_list = sub.add_parser("list", help="list oaths (open by default)")
    p_list.add_argument("-a", "--all", action="store_true", help="include done and broken")

    p_done = sub.add_parser("done", help="mark an oath kept")
    p_done.add_argument("number", type=int)

    p_break = sub.add_parser("break", help="mark an oath broken")
    p_break.add_argument("number", type=int)

    sub.add_parser("overdue", help="show open oaths past their due date")
    return parser


def format_oath(number: int, oath: Oath, today: dt.date, pal: Palette) -> str:
    status_style = {"OPEN": pal.cyan, "DONE": pal.dim, "BROKEN": pal.magenta}[oath.status]
    due = oath.due.isoformat() if oath.due else "-"
    due_text = pal.neon(f"due {due} !!") if oath.is_overdue(today) else pal.dim(f"due {due}")
    return f"{pal.magenta(f'#{number:<3}')} {status_style(f'{oath.status:<6}')} {due_text}  {oath.text}"


def run(args: argparse.Namespace, out: TextIO, pal: Palette) -> int:
    today = parse_date(args.today) if args.today else dt.date.today()
    book = OathFile(resolve_path(args.file))

    if args.command == "add":
        due = parse_due(args.due, today) if args.due else None
        oath = Oath("OPEN", today, due, " ".join(args.text))
        number = book.add(oath)
        book.save()
        print(f"{pal.neon('>> oath sworn')} {pal.magenta(f'#{number}')} {pal.cyan(oath.text)}", file=out)
        return 0

    if args.command in ("done", "break"):
        oath = book.get(args.number)
        if oath.status != "OPEN":
            raise OathError(f"oath #{args.number} is already {oath.status}")
        oath.status = "DONE" if args.command == "done" else "BROKEN"
        book.save()
        verdict = pal.cyan(">> oath kept") if oath.status == "DONE" else pal.magenta(">> oath broken")
        print(f"{verdict} #{args.number} {oath.text}", file=out)
        return 0

    rows = list(enumerate(book.oaths, 1))
    if args.command == "list":
        rows = [(n, o) for n, o in rows if args.all or o.status == "OPEN"]
        empty = "no oaths on the grid. swear one with `add`."
    else:  # overdue
        rows = [(n, o) for n, o in rows if o.is_overdue(today)]
        empty = "nothing overdue. cruising at 88 mph."
    if not rows:
        print(pal.dim(empty), file=out)
    for number, oath in rows:
        print(format_oath(number, oath, today, pal), file=out)
    # overdue exits 1 when there's something overdue, so it can gate scripts
    return 1 if args.command == "overdue" and rows else 0


def main(argv: Sequence[str] | None = None, out: TextIO | None = None, err: TextIO | None = None) -> int:
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err
    args = build_parser().parse_args(argv)
    try:
        return run(args, out, palette_for(out))
    except OathError as exc:
        print(f"{palette_for(err).magenta(f'{NAME}: error:')} {exc}", file=err)
        return 2


if __name__ == "__main__":
    sys.exit(main())
