"""The signed-receipt envelope: schema + Ed25519 sign/verify, subject-agnostic.

The envelope signs the *canonical JSON of a frozen subject model* without ever
inspecting the subject's fields. Because the signed content is a pure function of the
subject — no timestamps — identical subjects yield an identical payload-hash and (Ed25519
being deterministic) an identical signature. Verification recomputes the hash (catching
tampered content) and checks the detached signature under a **pinned** key (catching a
forged or swapped key).

``sign_payload`` and ``verify_signature`` operate on a generic ``SignedReceipt``. The
subject may be a frozen Pydantic model or a JSON-compatible mapping; the envelope never
branches on its keys or meaning."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Final, Literal, overload

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    TypeAdapter,
    ValidationError,
    model_serializer,
    model_validator,
)

from avow.canonical import JsonValue, canonical_bytes, content_hash
from avow.errors import (
    PayloadHashMismatch,
    ReceiptSchemaMismatch,
    SignatureBytesInvalid,
    SignerMismatch,
    SubjectInvalid,
    SubjectNotFrozen,
)


type Subject = BaseModel | JsonValue
type SubjectInput = BaseModel | JsonValue | Mapping[str, JsonValue]
_JSON_ADAPTER: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)
RECEIPT_SCHEMA: Final = "avow.receipt/v1"
# A receipt sealed by avow <= 0.4.x has no ``schema`` field at all. ``None`` is how the
# model records that absence; it is never accepted as a value someone wrote.
LEGACY_RECEIPT_SCHEMA: Final = None
_ACCEPTED_SCHEMAS: Final = (RECEIPT_SCHEMA, LEGACY_RECEIPT_SCHEMA)
_SCHEMA_KEYS: Final = ("schema", "receipt_schema")
_MISSING: Final = object()


class SignedReceipt[SubjectT: Subject](BaseModel):
    """A signed subject: the subject plus its content-hash, public key and signature.

    The envelope is generic over ``SubjectT`` and never inspects subject fields. It
    signs canonical JSON, so unrelated applications share the same receipt contract.

    ``schema`` is an unsigned label. New receipts carry ``avow.receipt/v1``; receipts
    sealed by avow <= 0.4.x carry no ``schema`` key and parse with
    ``receipt_schema=None``. Both forms sign the same bytes, so the label selects no
    different verification rule. A ``schema`` key that is present must be exactly v1."""

    model_config = ConfigDict(frozen=True, extra="forbid", serialize_by_alias=True)

    receipt_schema: Literal["avow.receipt/v1"] | None = Field(default=None, alias="schema")
    payload: SubjectT
    payload_hash: str
    public_key: str
    signature: str

    @model_validator(mode="before")
    @classmethod
    def require_supported_schema(cls, value: object) -> object:
        """Accept v1 or an absent schema (legacy); reject any other present value."""
        if isinstance(value, Mapping) and "schema" in value and value["schema"] != RECEIPT_SCHEMA:
            raise ReceiptSchemaMismatch("receipt schema is missing or unsupported")
        return value

    @model_serializer(mode="wrap")
    def omit_legacy_schema(self, handler: SerializerFunctionWrapHandler) -> object:
        """Write a legacy receipt back without a schema key, exactly as 0.4.x sealed it."""
        data = handler(self)
        if self.receipt_schema is LEGACY_RECEIPT_SCHEMA and isinstance(data, dict):
            for key in _SCHEMA_KEYS:
                data.pop(key, None)
        return data


def _require_frozen(payload: BaseModel) -> None:
    """Reject models whose fields may be rebound after sealing."""
    if payload.model_config.get("frozen") is not True:
        raise SubjectNotFrozen("Pydantic subjects must set model_config frozen=True")


def _validated_json(payload: object) -> JsonValue:
    """Validate and detach one value in the closed JSON data model."""
    candidate = dict(payload) if isinstance(payload, Mapping) else payload
    try:
        validated = _JSON_ADAPTER.validate_python(candidate, strict=True)
    except ValidationError as exc:
        raise SubjectInvalid("subject must contain only JSON-compatible values") from exc
    return copy.deepcopy(validated)


def _subject_json(payload: SubjectInput) -> JsonValue:
    """Convert either supported subject boundary to canonicalizable JSON."""
    if isinstance(payload, BaseModel):
        _require_frozen(payload)
        return _validated_json(payload.model_dump(mode="json"))
    return _validated_json(payload)


def _snapshot_subject(payload: SubjectInput) -> tuple[Subject, JsonValue]:
    """Detach validated state, then derive its one canonical JSON snapshot."""
    if isinstance(payload, BaseModel):
        _require_frozen(payload)
        stored_model = payload.model_copy(deep=True)
        snapshot = _validated_json(stored_model.model_dump(mode="json"))
        return stored_model, snapshot
    snapshot = _validated_json(payload)
    return snapshot, snapshot


def payload_digest(payload: SubjectInput) -> str:
    """Content-hash of a canonical subject (any frozen model)."""
    return content_hash(_subject_json(payload))


def _seal_snapshot(
    payload: Subject, snapshot: JsonValue, signing_key: SigningKey
) -> SignedReceipt[Subject]:
    """Derive one receipt entirely from a detached canonical snapshot."""
    message = canonical_bytes(snapshot)
    signature = signing_key.sign(message).signature
    return SignedReceipt(
        schema=RECEIPT_SCHEMA,
        payload=payload,
        payload_hash=content_hash(snapshot),
        public_key=bytes(signing_key.verify_key).hex(),
        signature=signature.hex(),
    )


@overload
def sign_payload[SubjectT: BaseModel](
    payload: SubjectT, signing_key: SigningKey
) -> SignedReceipt[SubjectT]: ...


@overload
def sign_payload(
    payload: JsonValue | Mapping[str, JsonValue], signing_key: SigningKey
) -> SignedReceipt[JsonValue]: ...


def sign_payload(  # type: ignore[misc]  # overloaded generic receipt is invariant
    payload: SubjectInput, signing_key: SigningKey
) -> SignedReceipt[Subject]:
    """Hash and Ed25519-sign any frozen subject into a verifiable receipt."""
    stored, snapshot = _snapshot_subject(payload)
    return _seal_snapshot(stored, snapshot, signing_key)


def _check_hash[SubjectT: Subject](receipt: SignedReceipt[SubjectT]) -> None:
    if payload_digest(receipt.payload) != receipt.payload_hash:
        raise PayloadHashMismatch("payload hash does not match payload content")


def _require_receipt_schema(receipt: object) -> None:
    """Re-check the label, since ``model_copy`` and ``model_construct`` skip validation."""
    if getattr(receipt, "receipt_schema", _MISSING) not in _ACCEPTED_SCHEMAS:
        raise ReceiptSchemaMismatch("receipt schema is missing or unsupported")


def _signed_message[SubjectT: Subject](receipt: SignedReceipt[SubjectT]) -> bytes:
    """The exact bytes the signer signed, for both accepted receipt forms.

    A legacy receipt (avow <= 0.4.x, no ``schema``) and a v1 receipt sign the same
    message: the RFC 8785 JCS bytes of the payload. ``schema`` is never part of it, so a
    v1 receipt with the label removed is byte-identical to the legacy receipt for the
    same payload and key. ``tests/test_legacy_receipts.py`` pins that identity against
    receipts sealed by the released 0.4.1."""
    return canonical_bytes(_subject_json(receipt.payload))


def _require_signer[SubjectT: Subject](
    receipt: SignedReceipt[SubjectT], expected_public_key: str
) -> None:
    """Require the caller-pinned signer, comparing hex by value."""
    if receipt.public_key.lower() != expected_public_key.lower():
        raise SignerMismatch("receipt public key is not the expected signer")


def _check_signature_bytes(message: bytes, signature: str, public_key: str) -> None:
    """Translate malformed or invalid signature bytes to one coded failure."""
    try:
        verifier = VerifyKey(bytes.fromhex(public_key))
        verifier.verify(message, bytes.fromhex(signature))
    except (ValueError, BadSignatureError) as exc:
        raise SignatureBytesInvalid("signature does not match payload") from exc


def verify_signature[SubjectT: Subject](
    receipt: SignedReceipt[SubjectT], *, expected_public_key: str
) -> None:
    """Verify content and signer against a caller-pinned key, without freshness.

    The receipt's embedded key is not trusted. Replay defence requires external state;
    see ``docs/OPERATIONS.md`` for the complete boundary."""
    _require_receipt_schema(receipt)
    _check_hash(receipt)
    _require_signer(receipt, expected_public_key)
    _check_signature_bytes(_signed_message(receipt), receipt.signature, expected_public_key)
