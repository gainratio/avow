# CLAUDE.md — Avow (`gainratio/avow`)

- **Status**: Public library + CLI (`avow` `0.5.3` on PyPI, `@gainratio/avow` `0.5.3` and `@gainratio/receipt-ui` `0.3.0` on npm).
- **Stack**: Python `>=3.12` (`pydantic`, `pynacl`, `rfc8785`, optional `typer` via `avow[cli]`), TypeScript ESM on Node `>=22.13` (`@noble/ed25519`, `canonicalize`), React `18 | 19` (`@gainratio/receipt-ui`).
- **Docs site**: `https://avow.gainratio.com/` (`gainratio/avow-docs`).

## Repository Layout

- `src/avow/` — Python signing, `RFC 8785` canonicalization (`canonical.py`), Ed25519 envelope (`envelope.py`, `verify.py`), key permissions (`keys.py`), atomic writes (`_atomic.py`), hash-chained JSONL ledger (`ledger.py`), and optional CLI (`cli.py`, `_console.py`).
- `ts/` — `@gainratio/avow` TypeScript package (`ts/src/`) and `@gainratio/receipt-ui` workspace package (`ts/packages/receipt-ui/`).
- `testdata/` — Shared cross-language canonical JSON, Ed25519 signature, tamper, and legacy `0.4.x` receipt vectors.
- `tests/` — Python unit, CLI, vector, packaging, README, docs, and workflow contract tests.
- `docs/` — `ARCHITECTURE.md`, `GETTING_STARTED.md`, `OPERATIONS.md`, and `docs/architecture/` interactive runtime map.

## Core Invariants

1. **Offline, zero-network verification**: Signing and verification perform local canonicalization (`RFC 8785` JCS), `SHA-256` hashing, and `Ed25519` math only — zero network sockets in runtime paths.
2. **Caller-pinned trust anchor**: Verification requires an explicit `expected_public_key` / `pinnedPublicKey` supplied out-of-band; `receipt.public_key` inside an untrusted receipt is never used as its own trust root.
3. **Cross-language byte parity & legacy compatibility**: Python (`avow`) and TypeScript (`@gainratio/avow`) produce identical canonical bytes and accept both `avow.receipt/v1` and pre-`0.5.0` schema-less receipts against shared `testdata/` vectors.
4. **Isolated packaging boundary**: The Python wheel and sdist ship only top-level `avow` (`[tool.hatch.build.targets.sdist]` includes only `/LICENSE`, `/README.md`, `/pyproject.toml`, `/src/avow`) and keep `typer` strictly inside `[project.optional-dependencies].cli`.
5. **Key file hygiene**: Signing from disk refuses private keys readable by group/others (`chmod 600` required; `avow.key_permissions_insecure`).

## Scarred Quality Gates

- `tests/test_readme_contract.py` & `tests/test_docs_contract.py` — Enforce the plain-English cold-reader opening, fixed `##` section order, zero banned internal jargon, live execution of `README.md` CLI and socket-disabled Python snippets, version parity (`0.5.3`), and valid relative links.
- `tests/test_packaging.py` & `tests/test_workflow_contract.py` — Enforce wheel/sdist top-level isolation (`frozenset({"avow"})`), sdist size `< 1 MB` and allowed root entries, co-install safety beside `assay-engine`, and checksum-pinned `gitleaks` rules.
- Complexity & coverage floors — `ruff` (`C901 <= 5`), `xenon --max-absolute A --max-modules A --max-average A`, `mypy --strict`, Python branch coverage `>= 90%`, and TypeScript Biome + `tsc --noEmit` + Vitest coverage + benchmark gate.

## Commands

```bash
# Python gate (lint, mypy --strict, xenon A/A/A, pytest >=90% branch cov)
uv run poe gate

# Workflow & release packaging contracts
uv run poe workflow-contract

# TypeScript & receipt-ui gates
pnpm --dir ts gate
pnpm --dir ts/packages/receipt-ui gate
```

## Engineering Standard Applicability

- **Configuration**: Runtime signing/verification takes explicit function arguments or CLI flags; zero environment variables are read by `avow` runtime code (see `.env.example`).
- **Observability / Accessibility**: Pure library + CLI (`avow`) emits deterministic dot-separated machine codes (`avow.verify.ok`, `avow.payload_hash_mismatch`); `@gainratio/receipt-ui` components carry accessible ARIA status roles and four-state verdicts.
