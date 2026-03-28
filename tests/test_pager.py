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
