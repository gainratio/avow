# Avow for TypeScript

## TL;DR

Avow creates signed, tamper-evident records. Give it any JSON evidence; it
returns a receipt that another machine can verify offline.

This is the `0.5.2` release of `@gainratio/avow`. It is the first under the `@gainratio`
scope; `@edgeproc/avow` `0.5.1` and older stay installable but are deprecated. `0.5.0`
was the first built from this repository.

## Usage

```ts
import {
  generateSeedHex,
  publicKeyHex,
  signPayload,
  verifySignature,
} from "@gainratio/avow";

const signingSeed = generateSeedHex();
const pinnedPublicKey = await publicKeyHex(signingSeed);
const receipt = await signPayload({ artifact: "sha256:abc" }, signingSeed);
await verifySignature(receipt, pinnedPublicKey);
```

The example derives the public key before the receipt exists. In a real verifier,
obtain `pinnedPublicKey` independently through a trusted configuration or distribution
channel—never from `receipt.public_key`. Every emitted receipt has schema
`avow.receipt/v1`. Receipts sealed by `@edgeproc/avow` `0.4.x` and older have no
`schema` key and still verify; a `schema` that is present must be exactly
`avow.receipt/v1`.

Verification proves that the payload is unchanged and was signed by the caller-pinned
key. It does not prove correctness, freshness, wall-clock time, or the honesty of the
signer.

Not a replay defence: a valid receipt verifies identically every time it is presented.
Callers needing replay protection sign their own nonce, audience, and expiry claims
into the payload and check them after `verifySignature`; the repository's
`docs/OPERATIONS.md` ("Replay protection is caller-owned") has the recipe.

The signing seed is unencrypted hex held by the caller. This package never reads key
files, so seed storage is the integrating application's responsibility; there is no
KMS/HSM seam. The Python package's file-mode check (`avow.key_permissions_insecure`,
raised by `load_signing_key` for a group- or other-accessible key file) has no
TypeScript counterpart because no TypeScript API loads a key from disk.
