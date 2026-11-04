"""Anthropic native Models API reader.

The native model-list endpoint enumerates models available through the
Messages API. It establishes text conversation support, not vision, tool use,
reasoning, context limits or other capabilities.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src import model_capabilities as mc
from src.model_capability_readers.base import (
    ModelCapabilityRecord,
    VENDOR_ANTHROPIC,
    as_list,
    build_capability,
    compact_str,
    stable_model_id_for,
)


vendor = VENDOR_ANTHROPIC


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
    model_id = compact_str(raw.get("id"))
    if not model_id:
        return None
    capability = build_capability(
        family=mc.FAMILY_CHAT,
        input_modalities=(mc.MODALITY_TEXT,),
        output_modalities=(mc.MODALITY_TEXT,),
    )
    return ModelCapabilityRecord(
        vendor=VENDOR_ANTHROPIC,
        model_id=model_id,
        stable_model_id=stable_model_id_for(
            VENDOR_ANTHROPIC, model_id, endpoint_id=endpoint_id, base_url=base_url
        ),
        display_name=compact_str(raw.get("display_name")) or model_id,
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
