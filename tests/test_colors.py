import io

from oathwave import cli
from oathwave.colors import Palette, color_enabled


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


def test_color_on_for_tty():
    assert color_enabled(FakeTTY()) is True


def test_color_off_when_not_a_tty():
    assert color_enabled(io.StringIO()) is False


def test_no_color_env_disables_color_even_on_tty(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert color_enabled(FakeTTY()) is False


def test_empty_no_color_is_ignored(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "")
    assert color_enabled(FakeTTY()) is True


def test_disabled_palette_passes_text_through():
    pal = Palette(False)
    for paint in (pal.cyan, pal.magenta, pal.neon, pal.dim):
        assert paint("grid") == "grid"


def test_enabled_palette_wraps_in_ansi():
    out = Palette(True).cyan("grid")
    assert out.startswith("\033[") and out.endswith("\033[0m") and "grid" in out


def test_cli_output_is_plain_when_not_a_tty(oath_file):
    out = io.StringIO()
    cli.main(["-f", str(oath_file), "add", "ship it"], out=out)
    cli.main(["-f", str(oath_file), "list"], out=out)
    assert "\033[" not in out.getvalue()


def test_cli_output_is_plain_with_no_color_on_tty(oath_file, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    out = FakeTTY()
    cli.main(["-f", str(oath_file), "add", "ship it"], out=out)
    assert "\033[" not in out.getvalue()


def test_cli_output_is_colored_on_tty(oath_file):
    out = FakeTTY()
    cli.main(["-f", str(oath_file), "add", "ship it"], out=out)
    assert "\033[" in out.getvalue()
