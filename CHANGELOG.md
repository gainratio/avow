# Changelog

All notable standalone Avow changes will be recorded here.

## [Unreleased]

- Rewrite the README in plain English: what a receipt is, a CLI walkthrough with real
  output, honest limits, and install steps. Move the technical detail into the new
  `docs/ARCHITECTURE.md`, add `docs/GETTING_STARTED.md` for new developers, and update
  the README contract tests to pin the new section order and ban internal jargon.
- Record that `0.5.0` is released and that `0.1.0` through `0.4.1` are now yanked on PyPI.

## [0.5.2]

- **npm package renamed to `@gainratio/avow`; old name deprecated.** `@edgeproc/avow`
  `0.5.1` and older keep installing (with a deprecation warning once the old name is
  deprecated); new releases ship only as `@gainratio/avow`. Change
  `npm install @edgeproc/avow` to `npm install @gainratio/avow` and update imports.
  No code change. The Python package `avow` moves to `0.5.2` in lockstep, unchanged.

## [0.5.1]

- **fix: typer is no longer a hard dependency (0.5.0 conflicted with edge-proc).** `0.5.0`
  required `typer>=0.16,<0.26` for every install, while `edge-proc` `0.5.0` needs
  `typer>=0.26.8` and `assay-engine[cli]` needs `typer>=0.27`, so no resolver could
  install them together. `pip install avow` is now the library alone (`pydantic`,
  `pynacl`, `rfc8785`); the `avow` command moves to the `cli` extra,
  `pip install "avow[cli]"`, which needs `typer>=0.27.2`. `click` is no longer a
  dependency. Running `avow` without the extra prints
  `avow.cli_extra_missing` and exits 2 instead of a traceback. A new test resolves
  avow beside `edge-proc`, `edgeproc-core`, and `assay-engine` from PyPI on every CI run.
- **Upgrade note:** if you use the command, install `avow[cli]`. The `0.5.0` key-mode rule
  still applies: `avow sign` refuses a signing key that any group or other user can read
  (`avow.key_permissions_insecure`); fix it with `chmod 600 <key>`.
- `@edgeproc/avow` moves to `0.5.1` in lockstep with no TypeScript changes.

## [0.5.0]

The first release built from this repository, and the first clean `avow` wheel.

- **Packaging:** the release verifier now refuses any wheel or sdist that installs a
  top-level name other than `avow`, and clean-installs the wheel beside
  `assay-engine` in both orders. Every `avow` release up to `0.4.1` (published from
  the pre-split `hseshadr/assay` repo) shipped top-level `assay/` and `writ/`
  packages that overwrote `assay-engine` and broke `from assay import ScoreResult`.
  This repo has never built those packages; the guard keeps it that way.
- **Upgrade note:** if an older `avow` overwrote or, on uninstall, removed
  `assay-engine`'s files, uninstall and reinstall `assay-engine` after upgrading:
  `pip uninstall assay-engine && pip install assay-engine`.
- **Planned:** once `0.5.0` is verified on PyPI, yank `0.1.0` through `0.4.1` there so
  resolvers stop picking a release that clobbers `assay-engine`.
- Rewrite the README to the portfolio template: a plain-language first screen, a
  runnable 60-second example whose real output is the hero, and a
  `tests/test_readme_contract.py` gate that re-runs that example with network access
  disabled. The Python and npm package descriptions now equal the README tagline.
- Extract the opaque JSON receipt and ledger kernel into the standalone `avow` project.
- Release Python `avow` and npm `@edgeproc/avow` together at `0.5.0`.
- Add exact-commit Python, Node 22, parity, mutation, example, artifact, and security gates.
- Add token-free trusted-publishing workflows that remain inactive until an exact version
  tag is pushed.
- **Security:** `load_signing_key` (and so `avow sign`) now fails closed with the new
  `KeyPermissionsInsecure` error, code `avow.key_permissions_insecure`, when a POSIX key
  file grants any group or other permission bit. Keys written by `keygen` or
  `save_signing_key` are already `0600` and load unchanged; the check is skipped on
  non-POSIX platforms. No receipt, ledger, or other wire format changes.
- Document the boundary plainly: Avow is not a replay defence, and the signing key is an
  unencrypted seed protected only by filesystem permissions with no KMS/HSM seam. Add
  caller-owned replay-protection and key-rotation recipes to `docs/OPERATIONS.md`.
