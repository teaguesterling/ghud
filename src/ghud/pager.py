"""Pager utility for Rich console output."""

from typing import Callable, Optional
from rich.console import Console


def render_with_pager(
    render_fn: Callable[[Console], None],
    console: Optional[Console] = None,
    no_pager: bool = False,
) -> None:
    """Render content, optionally wrapping in a pager.

    Args:
        render_fn: Function that takes a Console and prints to it.
        console: Rich Console instance. Created if not provided.
        no_pager: If True, render directly without pager.
    """
    if console is None:
        console = Console()

    if no_pager:
        render_fn(console)
    else:
        with console.pager(styles=True):
            render_fn(console)
