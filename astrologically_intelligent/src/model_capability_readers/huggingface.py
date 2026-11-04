"""Hugging Face Hub model-card metadata reader.

This module normalizes already-fetched Hub model-list records. Pipeline tags
are explicit task metadata; model names and tags are not treated as proof of
additional capabilities.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src import model_capabilities as mc
from src.model_capability_readers.base import (
    ModelCapabilityRecord,
    VENDOR_HUGGINGFACE,
    as_list,
    build_capability,
    compact_str,
    stable_model_id_for,
)


vendor = VENDOR_HUGGINGFACE


_TASKS = {
    "text-generation": (
        mc.FAMILY_CHAT, (mc.MODALITY_TEXT,), (mc.MODALITY_TEXT,), (),
    ),
    "conversational": (
        mc.FAMILY_CHAT, (mc.MODALITY_TEXT,), (mc.MODALITY_TEXT,), (),
    ),
    "image-to-text": (
        mc.FAMILY_CHAT, (mc.MODALITY_IMAGE,), (mc.MODALITY_TEXT,), (mc.CAP_VISION,),
    ),
    "visual-question-answering": (
        mc.FAMILY_CHAT, (mc.MODALITY_TEXT, mc.MODALITY_IMAGE), (mc.MODALITY_TEXT,), (mc.CAP_VISION,),
    ),
    "document-question-answering": (
        mc.FAMILY_CHAT, (mc.MODALITY_TEXT, mc.MODALITY_IMAGE), (mc.MODALITY_TEXT,), (mc.CAP_VISION, mc.CAP_FILES),
    ),
    "feature-extraction": (
        mc.FAMILY_EMBEDDING, (mc.MODALITY_TEXT,), (mc.MODALITY_EMBEDDING,), (),
    ),
    "sentence-similarity": (
        mc.FAMILY_RERANK, (mc.MODALITY_TEXT,), (mc.MODALITY_TEXT,), (),
    ),
    "text-classification": (
        mc.FAMILY_CLASSIFICATION, (mc.MODALITY_TEXT,), (mc.MODALITY_TEXT,), (),
    ),
    "image-classification": (
        mc.FAMILY_CLASSIFICATION, (mc.MODALITY_IMAGE,), (mc.MODALITY_TEXT,), (),
    ),
    "zero-shot-classification": (
        mc.FAMILY_CLASSIFICATION, (mc.MODALITY_TEXT,), (mc.MODALITY_TEXT,), (),
    ),
    "fill-mask": (
        mc.FAMILY_CHAT, (mc.MODALITY_TEXT,), (mc.MODALITY_TEXT,), (),
    ),
    "text-to-image": (
        mc.FAMILY_IMAGE, (mc.MODALITY_TEXT,), (mc.MODALITY_IMAGE,), (mc.CAP_IMAGE_GENERATION,),
    ),
    "image-to-image": (
        mc.FAMILY_IMAGE, (mc.MODALITY_IMAGE,), (mc.MODALITY_IMAGE,), (mc.CAP_IMAGE_EDITING,),
    ),
    "text-to-video": (
        mc.FAMILY_VIDEO, (mc.MODALITY_TEXT,), (mc.MODALITY_VIDEO,), (mc.CAP_VIDEO_GENERATION,),
    ),
    "automatic-speech-recognition": (
        mc.FAMILY_AUDIO, (mc.MODALITY_AUDIO,), (mc.MODALITY_TEXT,), (mc.CAP_TRANSCRIPTION, mc.CAP_AUDIO_INPUT),
    ),
    "audio-to-audio": (
        mc.FAMILY_AUDIO, (mc.MODALITY_AUDIO,), (mc.MODALITY_AUDIO,), (mc.CAP_AUDIO_INPUT, mc.CAP_AUDIO_OUTPUT),
    ),
    "text-to-speech": (
        mc.FAMILY_AUDIO, (mc.MODALITY_TEXT,), (mc.MODALITY_AUDIO,), (mc.CAP_TTS, mc.CAP_AUDIO_OUTPUT),
    ),
}


def _items(payload: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(payload, Mapping):
        values = payload.get("models")
        if values is None:
            values = payload.get("data")
        if values is None and (payload.get("id") or payload.get("modelId")):
            values = [payload]
    else:
        values = payload
    return tuple(item for item in as_list(values) if isinstance(item, Mapping))


def record_from_model(
    raw: Mapping[str, Any],
    *,
    endpoint_id: Any = "",
    base_url: Any = "",
) -> ModelCapabilityRecord | None:
    model_id = compact_str(raw.get("id") or raw.get("modelId"))
    if not model_id:
        return None

    task = compact_str(raw.get("pipeline_tag")).lower()
    task_shape = _TASKS.get(task)
    if task_shape is None:
        capability = mc.unknown_capability(
            source=mc.SOURCE_PROVIDER_READER,
            confidence=mc.CONFIDENCE_UNKNOWN,
        )
    else:
        family, inputs, outputs, capabilities = task_shape
        capability = build_capability(
            family=family,
            input_modalities=inputs,
            output_modalities=outputs,
            capabilities=capabilities,
        )

    return ModelCapabilityRecord(
        vendor=VENDOR_HUGGINGFACE,
        model_id=model_id,
        stable_model_id=stable_model_id_for(
            VENDOR_HUGGINGFACE, model_id, endpoint_id=endpoint_id, base_url=base_url
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
