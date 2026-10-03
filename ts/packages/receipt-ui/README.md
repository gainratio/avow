# @gainratio/receipt-ui

Render and verify an Avow `SignedReceipt` in React.

Your app signs a receipt at the engine level; this shows the user whether it
actually checks out. Drop in a `<ReceiptBadge>` or `<ReceiptPanel>`, hand it the
receipt and the one public key you trust, and it verifies on mount and renders
one of four clearly-distinct, fail-closed states:

- **Verifying…** — the check is in flight (the initial, not-yet-trusted state).
- **Verified** — the signature is valid *and* signed by the pinned key.
- **Not verified — tampered or invalid signature** — the verifier rejected it.
- **Not verified — untrusted signer** — the receipt's key is not the one you pinned.

Only a resolved verify under the pinned key ever reads as *Verified*. Anything
else — a rejection, an error, an unpinned key, or the moment before the check
returns — reads as not-verified. Status is conveyed by icon **and** text (never
color alone) inside an ARIA `role="status"` live region.

## Install

```sh
pnpm add @gainratio/receipt-ui @gainratio/avow react
```

`@gainratio/avow` and `react` are peer dependencies — the app provides them, so
there is a single avow instance and a single `SignedReceipt` type across the app
and this package.

| receipt-ui | `@gainratio/avow` peer | Receipt format |
| --- | --- | --- |
| 0.3.x | `^0.5.2` | `avow.receipt/v1` (carries a `schema` field), and pre-schema receipts with avow `0.5.3`+ |
| 0.1.x – 0.2.x | `^0.1.0` | pre-schema receipts (published from the old `hseshadr/assay` repo) |

This package shows avow's verdict and never overrides it. A receipt with no `schema`
(sealed by avow `0.4.x` or older) renders *Verified* with avow `0.5.3` or newer, and
*Not verified* with avow `0.5.0`–`0.5.2`, which wrongly refused it. A receipt with any
other `schema` value renders *Not verified*.

## Use

```tsx
import { ReceiptPanel } from "@gainratio/receipt-ui";

// `receipt` came from your engine (avow `signPayload`); `SIGNER_KEY` is the
// hex public key you trust. `verify` is optional — it defaults to avow's own
// `verifySignature`, so omit it unless your app injects a custom verifier.
<ReceiptPanel
  receipt={receipt}
  expectedPublicKey={SIGNER_KEY}
  renderPayload={(p) => <p>Score: {p.score}</p>}
/>;
```

`ReceiptBadge` takes the same `receipt` / `expectedPublicKey` / `verify` props
and renders just the one-line verdict; `ReceiptPanel` adds the envelope metadata
(algorithm, shortened signer key, payload hash, signature) and the payload body.

The verdict lives in the `useReceiptVerification` hook if you want to build your
own presentation; `StatusPill` is the standalone verdict chip.

## Localize

> **Requires `@gainratio/receipt-ui` 0.2.0 or newer.** 0.1.0 has no `labels`
> prop — it renders the built-in English strings and silently ignores the
> object. Check the version you resolved before filing a bug. See
> [`CHANGELOG.md`](CHANGELOG.md).

Every rendered string is injectable: pass a `labels` object (type
`ReceiptLabels`) to `StatusPill`, `ReceiptBadge` or `ReceiptPanel`. It is a
deep partial — omit anything to keep the built-in English default:

```tsx
<ReceiptPanel
  receipt={receipt}
  expectedPublicKey={SIGNER_KEY}
  labels={{
    status: { verified: { text: t("receipt.verified") } },
    panel: { receipt: t("receipt.section"), algorithm: t("receipt.algorithm") },
  }}
/>;
```

`labels.status` overrides the verdict chip per state (`checking` / `verified` /
`invalid` / `wrong-key`, each `{ text?, icon? }`); `labels.panel` overrides the
panel's meta strings (`receipt` — the section aria-label — plus `algorithm`,
`signerKey`, `payloadHash`, `signature`).

## Develop

This package lives in the [`hseshadr/avow`](https://github.com/hseshadr/avow)
pnpm workspace at `ts/packages/receipt-ui` and tests against the avow source
in `ts/`, not a published copy.

```sh
pnpm --dir ts install
pnpm --dir ts build                      # receipt-ui imports avow from ts/dist
pnpm --dir ts/packages/receipt-ui gate   # biome -> tsc strict -> vitest (+coverage) -> build
```

Releases are tag-driven and separate from avow's `vX.Y.Z` tags: bump
`package.json` and `CHANGELOG.md`, merge, then push `receipt-ui-vX.Y.Z`.
`.github/workflows/publish-receipt-ui.yml` publishes through npm trusted
publishing with provenance.

Tests build real avow receipts (valid, tampered, wrong-key) and replay avow's
shared golden vectors (`testdata/vectors/receipts.json`), asserting the
component reflects avow's own verdict — the property, not the shape.
