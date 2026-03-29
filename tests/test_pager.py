"""Tests for pager utility."""

import os
from io import StringIO
from unittest.mock import patch
from rich.console import Console
from ghud.pager import render_with_pager


def test_render_with_pager_disabled():
    """When no_pager=True, renders directly without pager."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=80)

    def render_fn(c: Console):
        c.print("Hello, world!")

    render_with_pager(render_fn, console=console, no_pager=True)
    output.seek(0)
    assert "Hello, world!" in output.read()


def test_render_short_output_skips_pager():
    """Short output that fits on screen should not trigger pager."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=80)

    def render_fn(c: Console):
        c.print("Short content")

    # Terminal is tall enough — should render directly, no pager
    with patch("ghud.pager.shutil.get_terminal_size", return_value=os.terminal_size((80, 50))):
        render_with_pager(render_fn, console=console, no_pager=False)
    output.seek(0)
    assert "Short content" in output.read()


def test_render_long_output_uses_pager():
    """Long output that exceeds terminal height should use pager."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=80)

    pager_used = False
    original_pager = console.pager

    def tracking_pager(**kwargs):
        nonlocal pager_used
        pager_used = True
        return original_pager(**kwargs)

    console.pager = tracking_pager

    def render_fn(c: Console):
        for i in range(100):
            c.print(f"Line {i}")

    # Terminal is very short — should trigger pager
    with patch("ghud.pager.shutil.get_terminal_size", return_value=os.terminal_size((80, 10))):
        render_with_pager(render_fn, console=console, no_pager=False)
    assert pager_used


def test_panel_borders_preserved_with_wide_content():
    """Pre-rendered panels with wide content should not be re-wrapped."""
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.text import Text

    body = (
        "text\n\n```\n"
        "┌──────────────────┬───────────────────┬─────────┬────────────┐\n"
        "│     file_path    │     file_ext      │  kind   │ size_bytes │\n"
        "└──────────────────┴───────────────────┴─────────┴────────────┘\n"
        "```\n"
    )

    output = StringIO()
    console = Console(file=output, force_terminal=True, width=80)

    def render_fn(c: Console):
        c.print(Panel(Markdown(body), title="Description", border_style="dim"))

    with patch("ghud.pager.shutil.get_terminal_size", return_value=os.terminal_size((80, 50))):
        render_with_pager(render_fn, console=console, no_pager=False)

    output.seek(0)
    rendered = output.read()
    lines = rendered.split("\n")

    # The buffer console renders the panel as ~10 lines. Without soft_wrap,
    # console.print() re-wraps the ANSI text into ~22 lines, breaking panel
    # borders. Verify the output wasn't inflated by re-wrapping.
    assert len(lines) <= 15, (
        f"Output has {len(lines)} lines — likely re-wrapped "
        f"(expected ~10 for a small panel)"
    )

    # Verify panel top and bottom borders survived intact on single lines
    border_lines = [
        l for l in lines
        if "╭" in Text.from_ansi(l).plain or "╰" in Text.from_ansi(l).plain
    ]
    assert len(border_lines) == 2, (
        f"Expected 2 border lines (╭ and ╰), got {len(border_lines)} — "
        f"borders were likely split across lines by re-wrapping"
    )
