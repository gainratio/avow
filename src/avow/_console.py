"""Console-script entry point; the Typer command lives behind the optional ``cli`` extra."""

from __future__ import annotations

import sys
from typing import Final

_MISSING_EXTRA: Final[str] = (
    "avow.cli_extra_missing: install the command with: pip install 'avow[cli]'\n"
)
_MISSING_EXIT: Final[int] = 2


def main() -> int:
    """Run the Typer adapter, or name the missing extra instead of a traceback."""
    try:
        from avow.cli import main as cli_main  # noqa: PLC0415 - optional extra
    except ModuleNotFoundError as error:
        if error.name != "typer":
            raise
        sys.stderr.write(_MISSING_EXTRA)
        return _MISSING_EXIT
    return cli_main()
