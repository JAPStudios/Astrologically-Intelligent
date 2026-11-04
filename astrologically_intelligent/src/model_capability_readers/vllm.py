"""vLLM model-list metadata reader.

The OpenAI-compatible model-list contract alone does not establish model
capabilities. vLLM's explicit max_model_len field is retained as a context
limit when present; other capability fields remain unknown.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src import model_capabilities as mc
from src.model_capability_readers.base import (
    ModelCapabilityRecord,
    VENDOR_VLLM,
    as_list,
    compact_str,
    int_limit,
    model_id_from,
    stable_model_id_for,
)


vendor = VENDOR_VLLM


def _items(payload: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(payload, Mapping):
        return ()
    values = payload.get("data")
    if values is None:
        values = payload.get("models")
    return tuple(item for item in as_list(values) if isinstance(item, Mapping))


def record_from_model(
    raw: Mapping[str, Any],
    *,
    endpoint_id: Any = "",
    base_url: Any = "",
) -> ModelCapabilityRecord | None:
    model_id = model_id_from(raw, "id", "root", "model")
    if not model_id:
        return None

    limits = {}
    context_tokens = int_limit(raw.get("max_model_len"))
    if context_tokens is not None:
        limits["context_tokens"] = context_tokens

    capability = mc.unknown_capability(
        source=mc.SOURCE_PROVIDER_READER,
        confidence=mc.CONFIDENCE_UNKNOWN,
    )
    if limits:
        capability = mc.ModelCapability.build(
            family=mc.FAMILY_UNKNOWN,
            limits=limits,
            source=mc.SOURCE_PROVIDER_READER,
            confidence=mc.CONFIDENCE_PROVIDER_REPORTED,
        )

    return ModelCapabilityRecord(
        vendor=VENDOR_VLLM,
        model_id=model_id,
        stable_model_id=stable_model_id_for(
            VENDOR_VLLM, model_id, endpoint_id=endpoint_id, base_url=base_url
        ),
        display_name=compact_str(raw.get("name")) or model_id,
        capability=capability,
        raw=raw,
    )


def records_from_payload(
    payload: Any,
    *,
    endpoint_id: Any = "",
    base_url: Any = "",
) -> tuple[ModelCapabilityRecord, ...]:
    records = []
    for item in _items(payload):
        record = record_from_model(item, endpoint_id=endpoint_id, base_url=base_url)
        if record is not None:
            records.append(record)
    return tuple(records)
