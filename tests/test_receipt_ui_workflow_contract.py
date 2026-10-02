"""Contract for the separate `@gainratio/receipt-ui` npm release rail."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import cast

import yaml

_WORKFLOW = Path(".github/workflows/publish-receipt-ui.yml")
_PACKAGE = Path("ts/packages/receipt-ui/package.json")
_ACTION_PIN = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


def _mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def _workflow() -> dict[str, object]:
    loader = yaml.BaseLoader(_WORKFLOW.read_text(encoding="utf-8"))
    try:
        return _mapping(loader.get_single_data())
    finally:
        loader.dispose()


def _jobs() -> dict[str, dict[str, object]]:
    return {name: _mapping(job) for name, job in _mapping(_workflow()["jobs"]).items()}


def _steps(job: dict[str, object]) -> list[dict[str, object]]:
    steps = job["steps"]
    assert isinstance(steps, list)
    return [_mapping(step) for step in steps]


def _commands(job: dict[str, object]) -> str:
    return "\n".join(str(step["run"]) for step in _steps(job) if "run" in step)


def test_should_fire_only_on_receipt_ui_tags_disjoint_from_avow_tags() -> None:
    # Given the receipt-ui trigger and the avow `v*.*.*` release trigger
    tags = _mapping(_mapping(_workflow()["on"])["push"])["tags"]
    # Then a receipt-ui tag can never start with "v" and so never fires publish.yml
    assert tags == ["receipt-ui-v*.*.*"]


def test_should_pin_every_action_to_an_immutable_commit() -> None:
    # Given every action the receipt-ui rail runs
    uses = [str(s["uses"]) for job in _jobs().values() for s in _steps(job) if "uses" in s]
    # Then no mutable tag or branch can change the reviewed workflow
    assert uses
    assert [use for use in uses if _ACTION_PIN.fullmatch(use) is None] == []


def test_should_mint_oidc_only_in_the_publish_job() -> None:
    # Given the workflow default and every job's permissions
    writers = [
        (name, scope)
        for name, job in _jobs().items()
        for scope, access in _mapping(job.get("permissions") or {}).items()
        if access == "write"
    ]
    # Then only the npm publish job can request an OIDC identity
    assert _workflow()["permissions"] == {}
    assert writers == [("publish", "id-token")]


def test_should_gate_the_package_before_packing_it() -> None:
    # Given the unprivileged build job
    build = _commands(_jobs()["build"])
    # Then both TypeScript gates run and the tag must equal the package version
    assert "pnpm --dir ts gate" in build
    assert "pnpm --dir ts/packages/receipt-ui gate" in build
    assert 'VERSION="${RELEASE_TAG#receipt-ui-v}"' in build
    assert build.index("receipt-ui gate") < build.index("pack --pack-destination")


def test_should_publish_the_reviewed_tarball_with_provenance() -> None:
    # Given the OIDC publish lane
    command = _commands(_jobs()["publish"])
    # Then it publishes a local file (not GitHub shorthand) with provenance
    assert "npm install --global npm@12.0.2" in command
    assert "npm publish ./release/*.tgz --access public --provenance" in command


def test_should_declare_avow_0_5_as_peer_and_this_repository_as_source() -> None:
    # Given the receipt-ui manifest that npm will serve
    package = _mapping(json.loads(_PACKAGE.read_text(encoding="utf-8")))
    # Then it targets avow 0.5 and points provenance at hseshadr/avow
    assert _mapping(package["peerDependencies"])["@gainratio/avow"] == "^0.5.2"
    assert _mapping(package["repository"]) == {
        "type": "git",
        "url": "git+https://github.com/hseshadr/avow.git",
        "directory": "ts/packages/receipt-ui",
    }
