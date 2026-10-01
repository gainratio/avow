"""Claim: avow installs beside our other published libraries.

avow 0.5.0 made ``typer>=0.16,<0.26`` a hard dependency while ``edge-proc`` 0.5.0
requires ``typer>=0.26.8``, so no resolver could install both. These tests resolve
this checkout together with the real neighbour releases from PyPI, with and without
the ``cli`` extra, and fail with the resolver's own explanation if they collide.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_NEIGHBOURS = (
    "edge-proc>=0.5.0",
    "edgeproc-core>=0.4.3",
    "assay-engine[cli]==0.5.0.dev3",
)


def _resolve(tmp_path: Path, avow_requirement: str) -> subprocess.CompletedProcess[str]:
    requirements = tmp_path / "requirements.in"
    requirements.write_text("\n".join((avow_requirement, *_NEIGHBOURS)) + "\n", encoding="utf-8")
    return subprocess.run(
        ["uv", "pip", "compile", "--python-version", "3.13", "--no-header", requirements],
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("extra", ["", "[cli]"])
def test_should_resolve_beside_edge_proc_edgeproc_core_and_assay_engine(
    tmp_path: Path, extra: str
) -> None:
    # Given this checkout (optionally with its CLI extra) and the real neighbour releases
    requirement = f"avow{extra} @ {Path.cwd().as_uri()}"
    # When one resolver has to satisfy all of them in a single environment
    result = _resolve(tmp_path, requirement)
    # Then it succeeds, and the whole environment shares one typer
    assert result.returncode == 0, result.stderr
    assert "\ntyper==" in f"\n{result.stdout}"
