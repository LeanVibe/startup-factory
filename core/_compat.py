"""Compatibility helpers providing graceful fallbacks when optional dependencies
(like ``rich``) are unavailable.

These stubs emulate the small portion of the APIs that the core services rely
on so the modules can still be imported and exercised in tests without pulling
in heavy UI dependencies. When the real dependency is installed the real classes
are re-exported.
"""
from __future__ import annotations

import contextlib
from typing import Any, Iterable, Optional

RICH_AVAILABLE = False

try:  # Prefer the real rich components when present
    from rich.console import Console  # type: ignore
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn  # type: ignore
    from rich.table import Table  # type: ignore
    from rich.panel import Panel  # type: ignore
    from rich.prompt import Prompt, Confirm  # type: ignore
    from rich.live import Live  # type: ignore
    RICH_AVAILABLE = True
except Exception:  # pragma: no cover - exercised when rich missing
    class Console:  # type: ignore[no-redef]
        """Minimal console that proxies to ``print``."""

        def print(self, *args: Any, **kwargs: Any) -> None:
            if args:
                print(*args)

    class _BasePrompt:
        @staticmethod
        def ask(prompt: str, *, choices: Optional[Iterable[str]] = None, default: Optional[str] = None) -> str:
            if default is not None:
                return default
            if choices:
                return next(iter(choices))
            return ""

    class Prompt(_BasePrompt):  # type: ignore[no-redef]
        pass

    class Confirm:  # type: ignore[no-redef]
        @staticmethod
        def ask(prompt: str, default: bool = False) -> bool:
            return default

    class Panel:  # type: ignore[no-redef]
        def __init__(self, renderable: Any, **_: Any) -> None:
            self.renderable = renderable

        def __str__(self) -> str:  # pragma: no cover - debug aid only
            return str(self.renderable)

    class Table:  # type: ignore[no-redef]
        def __init__(self, *_, **__):
            self.rows = []

        def add_column(self, *_: Any, **__: Any) -> None:  # pragma: no cover - no behaviour needed
            pass

        def add_row(self, *row: Any, **__: Any) -> None:  # pragma: no cover - diagnostic only
            self.rows.append(row)

    class SpinnerColumn:  # type: ignore[no-redef]
        pass

    class TextColumn:  # type: ignore[no-redef]
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

    class BarColumn:  # type: ignore[no-redef]
        pass

    class Progress(contextlib.AbstractContextManager):  # type: ignore[no-redef]
        """Context manager that ignores progress updates."""

        def __enter__(self) -> "Progress":
            return self

        def __exit__(self, *exc: Any) -> bool:
            return False

        # Task helpers -----------------------------------------------------
        def add_task(self, description: str, total: int = 1) -> str:
            return description

        def advance(self, *_: Any, **__: Any) -> None:
            pass

        def update(self, *_: Any, **__: Any) -> None:
            pass

    class Live(contextlib.AbstractContextManager):  # type: ignore[no-redef]
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def __enter__(self) -> "Live":
            return self

        def __exit__(self, *exc: Any) -> bool:
            return False

        def update(self, *_: Any, **__: Any) -> None:
            pass

__all__ = [
    "Console",
    "Panel",
    "Table",
    "Progress",
    "SpinnerColumn",
    "TextColumn",
    "BarColumn",
    "Prompt",
    "Confirm",
    "Live",
    "RICH_AVAILABLE",
]
