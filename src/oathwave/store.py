"""Read and write the plain-text oath file.

One oath per line, whitespace-separated, hand-editable:

    OPEN    2026-10-29  due:2026-11-05  ship the landing page
    DONE    2026-10-20  due:-           write the changelog

Lines that are blank or start with ``#`` are kept verbatim and ignored.
An oath's number is its 1-based position among oath lines.
"""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass
from pathlib import Path

from . import NAME

DEFAULT_FILENAME = "OATHS.txt"
FILE_ENV_VAR = f"{NAME.upper()}_FILE"
STATUSES = ("OPEN", "DONE", "BROKEN")
NO_DUE = "-"
# Every character str.splitlines() treats as a line boundary.
_LINE_BREAKS = frozenset("\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")


class OathError(Exception):
    """A user-facing problem with the oath file or a request."""


def check_text(text: str) -> str:
    """Return ``text`` stripped, or raise if it can't live on one oath line."""
    # The loader splits with str.splitlines(), so reject everything it splits on
    # (\n, \r, and friends like \v, \f, \x85, \u2028) -- not just \n and \r.
    if any(ch in _LINE_BREAKS for ch in text):
        raise OathError("oath text can't contain newlines or carriage returns -- keep it to one line")
    stripped = text.strip()
    if not stripped:
        raise OathError("oath text can't be empty")
    return stripped


@dataclass
class Oath:
    status: str
    created: dt.date
    due: dt.date | None
    text: str

    def __post_init__(self) -> None:
        # Validate here, not just in the CLI, so the store can never write a
        # line that it can't read back.
        if self.status not in STATUSES:
            raise OathError(f"unknown status {self.status!r}")
        self.text = check_text(self.text)

    def is_overdue(self, today: dt.date) -> bool:
        return self.status == "OPEN" and self.due is not None and self.due < today

    def to_line(self) -> str:
        check_text(self.text)  # text is mutable after construction
        due = self.due.isoformat() if self.due else NO_DUE
        return f"{self.status:<7} {self.created.isoformat()}  due:{due:<10}  {self.text}"


def parse_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        raise OathError(f"bad date {value!r} (want YYYY-MM-DD)") from None


def parse_line(line: str, lineno: int) -> Oath:
    parts = line.split(None, 3)
    if len(parts) < 4 or not parts[2].startswith("due:"):
        raise OathError(f"line {lineno}: expected 'STATUS YYYY-MM-DD due:DATE text'")
    status, created, due, text = parts
    status = status.upper()
    if status not in STATUSES:
        raise OathError(f"line {lineno}: unknown status {status!r}")
    due_value = due[len("due:"):]
    return Oath(
        status=status,
        created=parse_date(created),
        due=None if due_value == NO_DUE else parse_date(due_value),
        text=text.strip(),
    )


def resolve_path(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit)
    return Path(os.environ.get(FILE_ENV_VAR) or DEFAULT_FILENAME)


class OathFile:
    """An oath file loaded into memory, preserving comments and blank lines."""

    def __init__(self, path: Path) -> None:
        self.path = path
        # Each entry is either an Oath or a raw str (comment/blank) kept verbatim.
        self.lines: list[Oath | str] = []
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return  # no file yet: start empty, save() will create it
        except OSError as exc:
            raise OathError(_io_problem("read", path, exc)) from None
        except UnicodeDecodeError:
            raise OathError(f"can't read {path}: not a UTF-8 text file") from None
        for lineno, raw in enumerate(content.splitlines(), 1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                self.lines.append(raw)
            else:
                self.lines.append(parse_line(stripped, lineno))

    @property
    def oaths(self) -> list[Oath]:
        return [line for line in self.lines if isinstance(line, Oath)]

    def add(self, oath: Oath) -> int:
        self.lines.append(oath)
        return len(self.oaths)

    def get(self, number: int) -> Oath:
        oaths = self.oaths
        if not 1 <= number <= len(oaths):
            raise OathError(f"no oath #{number} (have {len(oaths)})")
        return oaths[number - 1]

    def save(self) -> None:
        body = "\n".join(l.to_line() if isinstance(l, Oath) else l for l in self.lines)
        try:
            self.path.write_text(body + "\n" if body else "", encoding="utf-8")
        except OSError as exc:
            raise OathError(_io_problem("write", self.path, exc)) from None


def _io_problem(verb: str, path: Path, exc: OSError) -> str:
    """Turn an OSError into a one-line, human-sized explanation."""
    if isinstance(exc, IsADirectoryError):
        reason = "it's a directory, not a file"
    elif isinstance(exc, PermissionError):
        reason = "permission denied"
    elif isinstance(exc, FileNotFoundError):
        reason = f"directory {str(path.parent)!r} doesn't exist"
    elif isinstance(exc, NotADirectoryError):
        reason = "part of the path is a file, not a directory"
    else:
        reason = (exc.strerror or str(exc)).lower()
    return f"can't {verb} {str(path)!r}: {reason}"
