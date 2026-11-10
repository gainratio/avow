# Contributing to Avow

Thank you for helping improve Avow. Please read [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) for a step-by-step developer walkthrough from fresh clone to pull request.

## Prerequisites

- **Python**: `3.12` or `3.13` and [`uv`](https://docs.astral.sh/uv/)
- **Node.js**: `>= 22.13` with `pnpm@11.5.0` (for TypeScript `@gainratio/avow` and `@gainratio/receipt-ui`)

## Setup

```bash
git clone https://github.com/gainratio/avow.git
cd avow
uv sync --frozen --all-groups
pnpm --dir ts install --frozen-lockfile
```

## Local Verification Before Opening a PR

Run the same checks that CI enforces:

```bash
uv run poe gate
uv run poe workflow-contract
pnpm --dir ts gate
pnpm --dir ts/packages/receipt-ui gate
```

What these verify:
- **`uv run poe gate`**: `ruff` lint & format, `mypy --strict`, `xenon` complexity (`A/A/A`), and `pytest` with `>= 90%` branch coverage (including `README.md` live CLI/Python execution and cross-language `testdata/` vectors).
- **`uv run poe workflow-contract`**: GitHub workflow security contracts, `gitleaks` rules, and sdist/wheel isolation (`avow` top-level package only).
- **`pnpm --dir ts gate`** & **`pnpm --dir ts/packages/receipt-ui gate`**: Biome lint/format, `tsc --noEmit`, Vitest coverage, package build, and release benchmark.

## Key Contribution Rules

1. **Keep Python and TypeScript receipts identical**: Any change to canonicalization, schema validation, or error codes must pass against shared vectors in `testdata/` in both `src/avow/` and `ts/src/`.
2. **Never trust self-declared signer keys**: Verification APIs must always check against caller-supplied pinned public keys.
3. **Keep core dependencies minimal**: `avow` core depends only on `pydantic`, `pynacl`, and `rfc8785`; CLI dependencies stay under the optional `cli` extra (`avow[cli]`).
4. **Security issues**: Do not open public issues for security vulnerabilities — follow [SECURITY.md](SECURITY.md).
