/**
 * Receipts sealed by avow <= 0.4.x (no `schema` field) keep verifying.
 *
 * `testdata/vectors/legacy_receipts.json` is frozen output of the RELEASED
 * `avow==0.4.1` wheel and `@edgeproc/avow@0.4.1` tarball; nothing here derives
 * it from this repo's code.
 *
 * Accepting a schema-less receipt is safe because `schema` is an unsigned label:
 * both forms sign the same bytes (RFC 8785 JCS of the payload), so a v1 receipt
 * with its label removed is byte-for-byte the receipt 0.4.x sealed for the same
 * payload and key. A `schema` that IS present must still be exactly v1.
 */

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { JsonValue } from "./canonical.js";
import {
  CanonicalizationFailed,
  PayloadHashMismatch,
  ReceiptSchemaMismatch,
  SignatureBytesInvalid,
  SignerMismatch,
} from "./errors.js";
import {
  RECEIPT_SCHEMA,
  type SignedReceipt,
  signPayload,
  verifySignature,
} from "./receipt.js";

type Receipt = SignedReceipt<JsonValue>;

interface LegacyVectors {
  seed_hex: string;
  public_key: string;
  python_receipts: Receipt[];
  typescript_receipts: Receipt[];
  typescript_outside_json_domain: Receipt[];
}

interface V1Vectors {
  public_key: string;
  receipts: Array<Omit<Receipt, "public_key">>;
}

function readVectors<T>(name: string): T {
  return JSON.parse(
    readFileSync(
      new URL(`../../testdata/vectors/${name}`, import.meta.url),
      "utf8",
    ),
  ) as T;
}

const golden = readVectors<LegacyVectors>("legacy_receipts.json");
const v1 = readVectors<V1Vectors>("receipts.json");
const legacy = [...golden.python_receipts, ...golden.typescript_receipts];
const KEY = golden.public_key;

function withoutSchema(receipt: Receipt): Receipt {
  const { schema: _label, ...rest } = receipt;
  return rest;
}

describe("receipts sealed by avow 0.4.1 verify", () => {
  it("has golden receipts from both released runtimes", () => {
    expect(golden.python_receipts.length).toBe(3);
    expect(golden.typescript_receipts.length).toBe(8);
  });

  it.each(legacy)("verifies legacy receipt %#", async (receipt) => {
    expect(Object.hasOwn(receipt, "schema")).toBe(false);
    await expect(verifySignature(receipt, KEY)).resolves.toBeUndefined();
  });
});

describe("removing the unsigned schema label grants nothing", () => {
  const pairs = golden.typescript_receipts.flatMap((old) =>
    v1.receipts
      .filter(
        (vector) =>
          JSON.stringify(vector.payload) === JSON.stringify(old.payload),
      )
      .map((vector) => [vector, old] as const),
  );

  it("pairs every shared payload with its v1 vector", () => {
    expect(pairs.length).toBe(7);
  });

  it.each(pairs)(
    "a stripped v1 vector is the identical legacy receipt (%#)",
    (vector, old) => {
      expect(withoutSchema({ ...vector, public_key: v1.public_key })).toEqual(
        old,
      );
    },
  );

  it("rejects a stripped v1 receipt with an edited payload", async () => {
    const stripped = withoutSchema(
      await signPayload({ d: "deny" }, golden.seed_hex),
    );
    const forged = { ...stripped, payload: { d: "allow" } };
    await expect(verifySignature(forged, KEY)).rejects.toThrow(
      PayloadHashMismatch,
    );
  });

  it("rejects a stripped v1 receipt with an edited payload and recomputed hash", async () => {
    const stripped = withoutSchema(
      await signPayload({ d: "deny" }, golden.seed_hex),
    );
    const other = await signPayload({ d: "allow" }, golden.seed_hex);
    const forged = {
      ...stripped,
      payload: other.payload,
      payload_hash: other.payload_hash,
    };
    await expect(verifySignature(forged, KEY)).rejects.toThrow(
      SignatureBytesInvalid,
    );
  });

  it("rejects a stripped receipt from a signer the caller did not pin", async () => {
    const stranger = withoutSchema(
      await signPayload({ d: "deny" }, "00".repeat(32)),
    );
    await expect(verifySignature(stranger, KEY)).rejects.toThrow(
      SignerMismatch,
    );
  });
});

describe("a present schema must be exactly v1", () => {
  it.each(["avow.receipt/v2", "avow.receipt/v0", "", null, undefined, 1])(
    "rejects a genuine legacy receipt labelled %s",
    async (schema) => {
      const labelled = {
        ...golden.python_receipts[0],
        schema,
      } as unknown as Receipt;
      await expect(verifySignature(labelled, KEY)).rejects.toThrow(
        ReceiptSchemaMismatch,
      );
    },
  );

  it("keeps sealing new receipts as v1", async () => {
    const receipt = await signPayload({ d: "deny" }, golden.seed_hex);
    expect(receipt.schema).toBe(RECEIPT_SCHEMA);
  });
});

it("rejects a legacy receipt outside the closed JSON domain", async () => {
  // 0.4.1 sealed 2^60; the JSON text JavaScript writes is a different integer in
  // Python, so it is not one payload in both languages and stays rejected.
  const [unsafe] = golden.typescript_outside_json_domain;
  if (unsafe === undefined) throw new Error("missing out-of-domain vector");
  await expect(verifySignature(unsafe, KEY)).rejects.toThrow(
    CanonicalizationFailed,
  );
});
