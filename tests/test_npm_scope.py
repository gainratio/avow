"""The npm packages publish under @gainratio; the old @edgeproc scope must not creep back."""

from __future__ import annotations

from pathlib import Path

_OLD_SCOPE = "@edgeproc/"
_MANIFESTS = (Path("ts/package.json"), Path("ts/packages/receipt-ui/package.json"))


def _release_surfaces() -> tuple[Path, ...]:
    workflows = tuple(sorted(Path(".github/workflows").glob("*.yml")))
    scripts = tuple(sorted(Path("scripts").glob("*.py")))
    return (*_MANIFESTS, *workflows, *scripts)


def test_should_publish_under_gainratio_scope() -> None:
    # Given the two npm manifests
    names = [path.read_text(encoding="utf-8") for path in _MANIFESTS]
    # Then both declare the new scope
    assert '"name": "@gainratio/avow"' in names[0]
    assert '"name": "@gainratio/receipt-ui"' in names[1]


def test_should_not_name_old_scope_in_manifests_workflows_or_release_scripts() -> None:
    # Given every file that decides what gets published or verified
    surfaces = _release_surfaces()
    # When each is searched for the retired scope
    offenders = [str(path) for path in surfaces if _OLD_SCOPE in path.read_text("utf-8")]
    # Then none still names it
    assert surfaces
    assert offenders == []
