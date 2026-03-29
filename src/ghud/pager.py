"""Pager utility for Rich console output."""

import os
import shutil
from io import StringIO
from typing import Callable, Optional

from rich.console import Console


def render_with_pager(
    render_fn: Callable[[Console], None],
    console: Optional[Console] = None,
    no_pager: bool = False,
) -> None:
    """Render content, optionally wrapping in a pager.

    Only pages if output exceeds the terminal height. Uses LESS=-R
    to ensure ANSI color codes are interpreted correctly.

    Args:
        render_fn: Function that takes a Console and prints to it.
        console: Rich Console instance. Created if not provided.
        no_pager: If True, render directly without pager.
    """
    if console is None:
        console = Console()

    if no_pager:
        render_fn(console)
        return

    # Render to a buffer first to check if paging is needed
    buf = StringIO()
    buf_console = Console(file=buf, width=console.size.width, force_terminal=True)
    render_fn(buf_console)
    rendered = buf.getvalue()

    line_count = rendered.count("\n")
    term_height = shutil.get_terminal_size().lines

    if line_count <= term_height - 2:
        # Fits on screen — print directly.
        # soft_wrap prevents re-wrapping pre-rendered ANSI text which would
        # break panel borders and table layouts.
        console.print(rendered, highlight=False, soft_wrap=True, end="")
    else:
        # Ensure less interprets ANSI escape codes
        os.environ.setdefault("LESS", "-R")
        with console.pager(styles=True):
            console.print(rendered, highlight=False, soft_wrap=True, end="")
