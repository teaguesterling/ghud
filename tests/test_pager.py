"""Tests for pager utility."""

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


def test_render_with_pager_enabled():
    """When no_pager=False, wraps in console.pager()."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=80)

    pager_entered = False

    original_pager = console.pager

    def tracking_pager(**kwargs):
        nonlocal pager_entered
        pager_entered = True
        return original_pager(**kwargs)

    console.pager = tracking_pager

    def render_fn(c: Console):
        c.print("Paged content")

    render_with_pager(render_fn, console=console, no_pager=False)
    assert pager_entered
