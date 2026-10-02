import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  generateSeedHex,
  type JsonValue,
  publicKeyHex,
  RECEIPT_SCHEMA,
  type SignedReceipt,
} from "@gainratio/avow";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import { ReceiptBadge } from "./ReceiptBadge.js";

// The shared golden vectors every Avow runtime (Python and TypeScript) replays.
// Rendering them proves the badge understands the receipt format avow emits
// today (`avow.receipt/v1`), not a fixture this package minted for itself.
interface VectorFile {
  public_key: string;
  receipts: Array<Omit<SignedReceipt<JsonValue>, "public_key">>;
}

const VECTORS = resolve(
  import.meta.dirname,
  "../../../../testdata/vectors/receipts.json",
);
const file = JSON.parse(readFileSync(VECTORS, "utf-8")) as VectorFile;
const first = file.receipts[0];
if (first === undefined) {
  throw new Error("receipts.json has no receipts");
}
const vector: SignedReceipt<JsonValue> = {
  ...first,
  public_key: file.public_key,
};

let untrustedKey: string;
beforeAll(async () => {
  untrustedKey = await publicKeyHex(generateSeedHex());
});

const verdict = () => screen.getByRole("status").getAttribute("data-status");

async function expectVerdict(
  receipt: SignedReceipt<JsonValue>,
  pinned: string,
  expected: string,
): Promise<void> {
  render(<ReceiptBadge receipt={receipt} expectedPublicKey={pinned} />);
  await waitFor(() => expect(verdict()).toBe(expected));
}

describe("ReceiptBadge against avow's shared receipt vectors", () => {
  it("renders VERIFIED for the golden avow.receipt/v1 vector", async () => {
    expect(vector.schema).toBe(RECEIPT_SCHEMA);
    await expectVerdict(vector, file.public_key, "verified");
  });

  it("renders INVALID when the vector's payload is tampered", async () => {
    const tampered = { ...vector, payload: { tampered: true } };
    await expectVerdict(tampered, file.public_key, "invalid");
  });

  it("renders WRONG-KEY when the vector is pinned to an untrusted signer", async () => {
    await expectVerdict(vector, untrustedKey, "wrong-key");
  });

  it("renders INVALID for a receipt without the avow.receipt/v1 schema", async () => {
    const legacy = { ...vector, schema: "avow.receipt/v0" } as never;
    await expectVerdict(legacy, file.public_key, "invalid");
  });

  it("pins hex keys by value like avow: an uppercase pin still verifies", async () => {
    await expectVerdict(vector, file.public_key.toUpperCase(), "verified");
  });
});
