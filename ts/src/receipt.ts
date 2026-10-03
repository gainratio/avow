/**
 * The signed-receipt envelope — the browser twin of Python `avow.envelope`.
 *
 * The envelope signs the canonical JSON of a subject without inspecting its
 * fields. Because the signed content is a pure function of the subject (no
 * timestamps), identical subjects yield an identical payload-hash and — Ed25519
 * being deterministic — an identical signature. So a receipt signed by the
 * Python kernel verifies here, and a receipt signed here verifies in Python,
 * byte-for-byte. The golden-vector suite gates that guarantee.
 *
 * Verification recomputes the hash (catching tampered content) and checks the
 * detached signature under a *pinned* key (catching a forged or swapped key),
 * mirroring `avow.envelope.verify_signature` step-for-step and error-for-error.
 */

import { etc, signAsync, verifyAsync } from "@noble/ed25519";
import {
  canonicalBytes,
  contentHash,
  type JsonValue,
  snapshotJsonValue,
} from "./canonical.js";
import {
  PayloadHashMismatch,
  ReceiptSchemaMismatch,
  SignatureBytesInvalid,
  SignerMismatch,
} from "./errors.js";
import { publicKeyHex } from "./keys.js";

/** The receipt envelope schema this runtime emits on every new receipt. */
export const RECEIPT_SCHEMA = "avow.receipt/v1" as const;

/**
 * A signed subject: the subject plus its content-hash, public key and signature.
 *
 * `schema` is an unsigned label. New receipts carry `avow.receipt/v1`; receipts
 * sealed by avow <= 0.4.x have no `schema` key at all and still verify. Both
 * forms sign the same bytes, so the label selects no different rule. A `schema`
 * key that is present must be exactly `avow.receipt/v1`.
 */
export interface SignedReceipt<S extends JsonValue> {
  schema?: typeof RECEIPT_SCHEMA;
  payload: S;
  payload_hash: string;
  public_key: string;
  signature: string;
}

/** Hash and Ed25519-sign a subject into a verifiable receipt, using a hex seed. */
export async function signPayload<S extends JsonValue>(
  payload: S,
  seedHex: string,
): Promise<SignedReceipt<S> & { schema: typeof RECEIPT_SCHEMA }> {
  const snapshot = snapshotJsonValue(payload) as S;
  const message = canonicalBytes(snapshot);
  const signature = await signAsync(message, etc.hexToBytes(seedHex));
  return {
    schema: RECEIPT_SCHEMA,
    payload: snapshot,
    payload_hash: await contentHash(snapshot),
    public_key: await publicKeyHex(seedHex),
    signature: etc.bytesToHex(signature),
  };
}

async function checkSignatureBytes(
  message: Uint8Array,
  signatureHex: string,
  publicKeyHexPinned: string,
): Promise<void> {
  let ok: boolean;
  try {
    ok = await verifyAsync(
      etc.hexToBytes(signatureHex),
      message,
      etc.hexToBytes(publicKeyHexPinned),
    );
  } catch (cause) {
    throw new SignatureBytesInvalid("signature does not match payload", {
      cause,
    });
  }
  if (!ok) {
    throw new SignatureBytesInvalid("signature does not match payload");
  }
}

/**
 * Accept the v1 label or no `schema` key at all (the avow <= 0.4.x form).
 * A key that is present with any other value, `undefined` included, is refused.
 */
function requireAcceptedSchema(receipt: object): void {
  if (!Object.hasOwn(receipt, "schema")) return;
  if ((receipt as { schema?: unknown }).schema !== RECEIPT_SCHEMA) {
    throw new ReceiptSchemaMismatch("receipt schema is missing or unsupported");
  }
}

/**
 * The exact bytes the signer signed, for both accepted receipt forms: the RFC
 * 8785 JCS bytes of the payload. `schema` is never part of them, so a v1
 * receipt with the label removed is byte-identical to the legacy receipt for
 * the same payload and key (pinned against the released 0.4.1 by
 * `legacyReceipt.test.ts`).
 */
function signedMessage(snapshot: JsonValue): Uint8Array {
  return canonicalBytes(snapshot);
}

/**
 * Verify a receipt against a *pinned* signer key. Fail-closed: throws a coded
 * `ReceiptSchemaMismatch` (a `schema` is present but is not `avow.receipt/v1`;
 * a receipt with no `schema` is the avow <= 0.4.x form and verifies),
 * `PayloadHashMismatch` (content hash disagrees), `SignerMismatch` (embedded key
 * is not the pinned signer), or `SignatureBytesInvalid` (the signature does not
 * verify). The latter two both extend the published `SignatureInvalid` base.
 *
 * Proves **who signed it** and **that it is unmodified**. Does NOT prove
 * *freshness* — that this is the first time the receipt has been presented, or
 * that it was made recently. A signature binds content to a signer; it cannot
 * bind it to an occasion, so a genuine receipt captured on the wire verifies here
 * forever. That is the same property that makes offline verification years later
 * possible at all. This package ships the envelope only — there is no ledger in
 * the browser build — so if you need "have I seen this before?", keep that state
 * yourself (a server-side nonce, or the Python `avow.ledger` chain).
 *
 * The order mirrors Python exactly: require an accepted receipt schema first,
 * recompute the payload hash, then reject any receipt whose embedded `public_key`
 * is not the caller-pinned key — independent of the signature, because that field
 * lives outside the signed payload and a re-signed forgery can swap it in — then
 * verify the detached signature under the pinned key.
 */
export async function verifySignature<S extends JsonValue>(
  receipt: SignedReceipt<S>,
  expectedPublicKey: string,
): Promise<void> {
  requireAcceptedSchema(receipt);
  const snapshot = snapshotJsonValue(receipt.payload);
  if ((await contentHash(snapshot)) !== receipt.payload_hash) {
    throw new PayloadHashMismatch(
      "payload hash does not match payload content",
    );
  }
  // Hex is case-insensitive, so pin by value, not by spelling (mirrors Python
  // avow.envelope): a lowercase embedded key and an uppercase pinned key are the
  // SAME signer and must not read as a mismatch.
  if (receipt.public_key.toLowerCase() !== expectedPublicKey.toLowerCase()) {
    // Provenance failure, coded apart from a bytes failure: signed by a key
    // the caller does not trust, so the signature is never even checked.
    throw new SignerMismatch("receipt public key is not the expected signer");
  }
  await checkSignatureBytes(
    signedMessage(snapshot),
    receipt.signature,
    expectedPublicKey,
  );
}
