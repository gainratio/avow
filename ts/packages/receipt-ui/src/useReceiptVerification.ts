import type { JsonValue, SignedReceipt } from "@edgeproc/avow";
import { useEffect, useState } from "react";
import type { ReceiptStatus, VerifyFn } from "./types.js";

/**
 * Drive a receipt through the four render states.
 *
 * Fail-closed by construction: the initial state is `checking`, and the only
 * transition to `verified` is the injected `verify` resolving. A pin mismatch is
 * caught up front — independent of any crypto — so an untrusted signer is never
 * even handed to the verifier. Any rejection lands on `invalid`.
 */
export function useReceiptVerification<S extends JsonValue>(
  receipt: SignedReceipt<S>,
  expectedPublicKey: string,
  verify: VerifyFn<S>,
): ReceiptStatus {
  const [status, setStatus] = useState<ReceiptStatus>("checking");

  useEffect(() => {
    // Hex is case-insensitive: pin by value, exactly as avow's verifySignature
    // does, so the same signer spelled in another case is not "untrusted".
    if (receipt.public_key.toLowerCase() !== expectedPublicKey.toLowerCase()) {
      setStatus("wrong-key");
      return;
    }
    setStatus("checking");
    let active = true;
    const run = async (): Promise<void> => {
      let next: ReceiptStatus;
      try {
        await verify(receipt, expectedPublicKey);
        next = "verified";
      } catch {
        next = "invalid";
      }
      if (active) {
        setStatus(next);
      }
    };
    void run();
    return () => {
      active = false;
    };
  }, [receipt, expectedPublicKey, verify]);

  return status;
}
