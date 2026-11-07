"""Reader for bare OpenAI-compatible model-list payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src import model_capabilities as mc
from src.model_capability_readers.base import (
    ModelCapabilityRecord,
    VENDOR_GENERIC_OPENAI,
    compact_str,
    model_id_from,
    openai_model_items,
    stable_model_id_for,
)


vendor = VENDOR_GENERIC_OPENAI


def record_from_model(
    raw: Mapping[str, Any],
    *,
    vendor_id: str = VENDOR_GENERIC_OPENAI,
    endpoint_id: Any = "",
    base_url: Any = "",
) -> ModelCapabilityRecord | None:
    # Generic gateways do not share one model identifier field. Accept common
    # identity-only keys, but never infer capabilities from their values.
    model_id = model_id_from(raw, "key", "slug", "id", "model", "name")
    if not model_id:
        return None
    capability = mc.unknown_capability(
        source=mc.SOURCE_PROVIDER_READER,
        confidence=mc.CONFIDENCE_UNKNOWN,
    )
    return ModelCapabilityRecord(
        vendor=vendor_id,
        model_id=model_id,
        stable_model_id=stable_model_id_for(vendor_id, model_id, endpoint_id=endpoint_id, base_url=base_url),
        display_name=compact_str(raw.get("display_name") or raw.get("name")),
        capability=capability,
        raw=raw,
    )


def records_from_payload(
    payload: Any,
    *,
    vendor_id: str = VENDOR_GENERIC_OPENAI,
    endpoint_id: Any = "",
    base_url: Any = "",
) -> tuple[ModelCapabilityRecord, ...]:
    # Most gateways use {"data": [...]} or {"models": [...]}; a few return the
    # array directly. Keep this fallback deliberately identity-only.
    if isinstance(payload, list):
        items = tuple(item for item in payload if isinstance(item, Mapping))
    else:
        items = openai_model_items(payload)
    records: list[ModelCapabilityRecord] = []
    seen: set[str] = set()
    for item in items:
        record = record_from_model(item, vendor_id=vendor_id, endpoint_id=endpoint_id, base_url=base_url)
        if record and record.model_id not in seen:
            records.append(record)
            seen.add(record.model_id)
    return tuple(records)
