"""Claim: the library never forces CLI dependencies on consumers.

``pip install avow`` gives the receipt and ledger library only; the ``avow`` command
needs ``pip install 'avow[cli]'``. Without the extra the command must say so with a
stable code, not crash with a traceback.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from test_cli import _build_wheel, _create_environment, _run_checked

import avow._console as console
import avow.cli as cli_module

_MISSING = "avow.cli_extra_missing: install the command with: pip install 'avow[cli]'\n"
_CORE_PROBE = "import avow; assert avow.sign_payload; import importlib.util as u; "
_CORE_PROBE += "assert u.find_spec('typer') is None"


def _run(command: Path, cwd: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(command), *arguments], cwd=cwd, check=False, capture_output=True, text=True
    )


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build_wheel(tmp_path_factory.mktemp("extra-wheel"))


def _install(root: Path, requirement: str) -> Path:
    python = _create_environment(root / "environment")
    _run_checked(["uv", "pip", "install", "--python", str(python), requirement])
    return python


def test_should_refuse_the_command_with_a_stable_code_without_the_extra(
    wheel: Path, tmp_path: Path
) -> None:
    # Given the wheel installed on its own, as a library consumer would
    python = _install(tmp_path, str(wheel))
    # When the library is imported and the console script is run
    core = _run(python, tmp_path, "-c", _CORE_PROBE)
    result = _run(python.parent / "avow", tmp_path, "keygen", "--out", "signing.key")
    # Then the library works without typer and the command names the missing extra
    assert (core.returncode, core.stderr) == (0, "")
    assert (result.returncode, result.stdout, result.stderr) == (2, "", _MISSING)
    assert not (tmp_path / "signing.key").exists()


def test_should_run_the_command_when_installed_with_the_cli_extra(
    wheel: Path, tmp_path: Path
) -> None:
    # Given the wheel installed with its cli extra
    python = _install(tmp_path, f"avow[cli] @ {wheel.as_uri()}")
    # When the console script generates a key
    result = _run(python.parent / "avow", tmp_path, "keygen", "--out", "signing.key")
    # Then the extra pulled in a working command
    assert (result.returncode, result.stdout, result.stderr) == (0, "avow.keygen.ok\n", "")


def test_should_report_the_missing_extra_in_process(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given an interpreter where typer cannot be imported
    monkeypatch.delitem(sys.modules, "avow.cli", raising=False)
    monkeypatch.setitem(sys.modules, "typer", None)
    # When the console entry point runs
    exit_code = console.main()
    # Then it exits 2 with only the stable install hint
    assert (exit_code, capsys.readouterr()) == (2, ("", _MISSING))


def test_should_not_mask_an_unrelated_missing_module(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given an interpreter where a core dependency, not the CLI extra, is missing
    monkeypatch.delitem(sys.modules, "avow.cli", raising=False)
    monkeypatch.setitem(sys.modules, "nacl.signing", None)
    # When the console entry point runs, then the real import error surfaces
    with pytest.raises(ModuleNotFoundError) as caught:
        console.main()
    assert caught.value.name == "nacl.signing"


def test_should_delegate_to_the_typer_adapter_when_the_extra_is_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given the CLI extra is importable
    monkeypatch.setattr(cli_module, "main", lambda: 7)
    # When the console entry point runs, then it returns the adapter's exit code
    assert console.main() == 7
