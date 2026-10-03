"""Receipts sealed by avow <= 0.4.x (no ``schema`` field) keep verifying.

The golden file ``testdata/vectors/legacy_receipts.json`` is frozen output of the
RELEASED 0.4.1 wheel and npm tarball; nothing here derives it from this repo's code.

Why accepting a schema-less receipt is safe: ``schema`` is an unsigned envelope label.
Both forms sign the same bytes (RFC 8785 JCS of the payload), so a v1 receipt with its
label removed is byte-for-byte the receipt 0.4.x would have sealed for the same payload
and key. Removing the label changes no payload, hash, signer, or signature rule. Any
schema that *is* present must still be exactly ``avow.receipt/v1``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from nacl.signing import SigningKey
from pydantic import BaseModel, ConfigDict

from avow import LedgerHead, SignedReceipt, sign_payload, verify_ledger, verify_signature
from avow.canonical import JsonValue
from avow.errors import (
    CanonicalizationFailed,
    PayloadHashMismatch,
    ReceiptSchemaMismatch,
    SignatureBytesInvalid,
    SignerMismatch,
)

_GOLDEN = json.loads(Path("testdata/vectors/legacy_receipts.json").read_text(encoding="utf-8"))
_V1 = json.loads(Path("testdata/vectors/receipts.json").read_text(encoding="utf-8"))
_KEY: str = _GOLDEN["public_key"]
_LEGACY: list[dict[str, JsonValue]] = _GOLDEN["python_receipts"] + _GOLDEN["typescript_receipts"]


class _Evidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str
    score: float
    tags: list[str]


def _without_schema(receipt: dict[str, JsonValue]) -> dict[str, JsonValue]:
    return {field: value for field, value in receipt.items() if field != "schema"}


@pytest.mark.parametrize("legacy", _LEGACY)
def test_should_verify_a_receipt_sealed_by_avow_0_4_1(legacy: dict[str, JsonValue]) -> None:
    # Given a receipt the released 0.4.1 sealed, with no schema field
    assert "schema" not in legacy
    # When it is parsed and verified against the pinned signer
    receipt = SignedReceipt[JsonValue].model_validate(legacy)
    # Then it verifies exactly as it did under 0.4.1
    verify_signature(receipt, expected_public_key=_KEY)


@pytest.mark.parametrize("legacy", _GOLDEN["python_receipts"])
def test_should_verify_a_legacy_receipt_into_a_typed_model_subject(
    legacy: dict[str, JsonValue],
) -> None:
    receipt = SignedReceipt[_Evidence].model_validate_json(json.dumps(legacy))

    verify_signature(receipt, expected_public_key=_KEY)

    assert receipt.receipt_schema is None


@pytest.mark.parametrize("legacy", _LEGACY)
def test_should_round_trip_a_legacy_receipt_without_inventing_a_schema(
    legacy: dict[str, JsonValue],
) -> None:
    receipt = SignedReceipt[JsonValue].model_validate(legacy)

    assert receipt.model_dump(mode="json") == legacy
    assert json.loads(receipt.model_dump_json()) == legacy


def test_should_verify_a_ledger_written_by_avow_0_4_1(tmp_path: Path) -> None:
    # Given the ledger file and head 0.4.1 wrote for three legacy receipts
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("\n".join(_GOLDEN["python_ledger"]["lines"]) + "\n", encoding="utf-8")
    head = LedgerHead.model_validate(_GOLDEN["python_ledger"]["head"])
    # When the current verifier walks it
    receipts = verify_ledger(
        ledger, SignedReceipt[_Evidence], expected_public_key=_KEY, expected_head=head
    )
    # Then every receipt and link verifies
    assert len(receipts) == 3


_SAME_PAYLOAD = [
    (v1, legacy)
    for legacy in _GOLDEN["typescript_receipts"]
    for v1 in _V1["receipts"]
    if v1["payload"] == legacy["payload"]
]


def test_should_pair_every_shared_payload_with_its_v1_vector() -> None:
    assert len(_SAME_PAYLOAD) == 7


@pytest.mark.parametrize(("v1", "legacy"), _SAME_PAYLOAD)
def test_should_make_a_stripped_v1_receipt_identical_to_the_legacy_receipt(
    v1: dict[str, JsonValue], legacy: dict[str, JsonValue]
) -> None:
    # Given a v1 vector and the receipt 0.4.1 sealed for the same payload and seed
    stripped = _without_schema({**v1, "public_key": _V1["public_key"]})
    # Then removing the unsigned label yields the identical legacy receipt, so a
    # downgrade carries no payload, hash, signer, or signature the signer did not make
    assert stripped == legacy


def _stripped_v1() -> dict[str, JsonValue]:
    receipt = sign_payload({"decision": "deny"}, SigningKey(bytes.fromhex(_GOLDEN["seed_hex"])))
    return _without_schema(receipt.model_dump(mode="json"))


def _forgeries() -> list[tuple[dict[str, JsonValue], type[Exception]]]:
    stripped = _stripped_v1()
    other = sign_payload({"decision": "allow"}, SigningKey(bytes(32))).model_dump(mode="json")
    rehashed = sign_payload({"decision": "allow"}, SigningKey(bytes.fromhex(_GOLDEN["seed_hex"])))
    return [
        ({**stripped, "payload": {"decision": "allow"}}, PayloadHashMismatch),
        (
            {**stripped, "payload": {"decision": "allow"}, "payload_hash": rehashed.payload_hash},
            SignatureBytesInvalid,
        ),
        (_without_schema(other), SignerMismatch),
    ]


@pytest.mark.parametrize(("forged", "error"), _forgeries())
def test_should_reject_a_stripped_v1_receipt_whose_signed_fields_were_altered(
    forged: dict[str, JsonValue], error: type[Exception]
) -> None:
    receipt = SignedReceipt[JsonValue].model_validate(forged)

    with pytest.raises(error):
        verify_signature(receipt, expected_public_key=_KEY)


@pytest.mark.parametrize("schema", ["avow.receipt/v2", "avow.receipt/v0", "", None, 1])
def test_should_reject_a_present_schema_that_is_not_v1(schema: object) -> None:
    # Given a genuine legacy receipt that now claims some other envelope schema
    labelled = {**_GOLDEN["python_receipts"][0], "schema": schema}
    # Then only an absent schema selects the legacy form; anything present must be v1
    with pytest.raises(ReceiptSchemaMismatch):
        SignedReceipt[JsonValue].model_validate(labelled)


def test_should_reject_a_legacy_receipt_outside_the_closed_json_domain() -> None:
    # 0.4.1 TypeScript sealed an integer above 2^53-1; the JSON text JavaScript emits
    # is a different integer in Python, so it is not one payload in both languages.
    legacy = _GOLDEN["typescript_outside_json_domain"][0]
    receipt = SignedReceipt[JsonValue].model_validate(legacy)

    with pytest.raises(CanonicalizationFailed):
        verify_signature(receipt, expected_public_key=_KEY)


def test_should_keep_sealing_new_receipts_as_v1() -> None:
    receipt = sign_payload({"decision": "deny"}, SigningKey(bytes.fromhex(_GOLDEN["seed_hex"])))

    assert receipt.model_dump(mode="json")["schema"] == "avow.receipt/v1"
