# Changelog

`@gainratio/receipt-ui` is versioned separately from the repo's `v*`-tagged
`avow` / `@gainratio/avow` co-releases (see the root `CHANGELOG.md`) and
released from `receipt-ui-vX.Y.Z` tags.

## [0.3.0] - Unreleased

### Changed

- **Renamed to `@gainratio/receipt-ui`; old name deprecated.** 0.3.0 is the first
  release under the new name. `@edgeproc/receipt-ui` 0.2.0 and older keep installing.
- **Moved to `hseshadr/avow`.** The package now lives beside the avow kernel it
  renders (`ts/packages/receipt-ui`). 0.1.0 and 0.2.0 were published from
  `hseshadr/assay`, which dropped the package when it split from avow.
- **Peer dependency is now `@gainratio/avow ^0.5.2`** (was `@edgeproc/avow ^0.1.0`). Receipts
  carry `schema: "avow.receipt/v1"`; a receipt without it renders as
  *Not verified*, because avow 0.5 rejects it.

### Fixed

- **Signer pinning is case-insensitive, matching avow.** An uppercase pinned key
  and a lowercase embedded key are the same signer. 0.2.0 compared the strings
  exactly and showed a genuine receipt as *untrusted signer*.

## [0.2.0] - 2026-07-25

### Added

- **Injectable labels (i18n).** Every rendered string can now be overridden via
  an optional `labels` prop (type `ReceiptLabels`) on `StatusPill`,
  `ReceiptBadge` and `ReceiptPanel`: per-verdict `{ text?, icon? }` for the four
  `ReceiptStatus` states, plus the panel's envelope-metadata labels (the
  `receipt` section aria-label, `algorithm`, `signerKey`, `payloadHash`,
  `signature`). The prop is a deep partial merged field-by-field with the
  built-in English defaults, so a consumer that passes nothing renders exactly
  the 0.1.0 strings — no breaking changes. New exported types: `ReceiptLabels`,
  `PanelLabels`, `StatusLabelOverride`.

## [0.1.0] - 2026-07-22

Initial release: `ReceiptBadge`, `ReceiptPanel`, `StatusPill`,
`useReceiptVerification` and `shortenHex` — a fail-closed, four-state receipt
verdict UI over `@edgeproc/avow`.
