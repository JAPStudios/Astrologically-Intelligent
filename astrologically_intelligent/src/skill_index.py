"""Semantic ranking for the native Odysseus skill registry.

This deliberately reuses an already-ready ToolIndex embedding lane. Skill search
must never trigger a cold embedding-model load in the foreground request path;
the existing lexical matcher remains the fallback until startup prewarm finishes.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections import OrderedDict
from typing import Any, Dict, List, Sequence

from src.embedding_lanes import LANE_FASTEMBED

logger = logging.getLogger(__name__)

_CACHE_LIMIT = 16
_cache_lock = threading.Lock()
_corpus_cache: "OrderedDict[str, List[List[float]]]" = OrderedDict()
_quality_model_cache: "OrderedDict[str, Any]" = OrderedDict()


def _semantic_text(skill: Dict[str, Any]) -> str:
    parts = [
        f"Skill: {skill.get('name', '')}",
        str(skill.get("description") or skill.get("title") or ""),
        f"Use when: {skill.get('when_to_use') or skill.get('problem') or ''}",
    ]
    tags = skill.get("tags") or []
    if tags:
        parts.append("Tags: " + ", ".join(str(tag) for tag in tags[:24]))
    procedure = skill.get("procedure") or skill.get("steps") or []
    if procedure:
        parts.append("Procedure: " + " ".join(str(step) for step in procedure[:8]))
    # Imported skills can be very large. Ranking needs intent, not full reference
    # material or bundled templates.
    return "\n".join(parts)[:6000]


def _choose_lane(index: Any) -> Any:
    lanes = list(getattr(index, "embedding_lanes", ()) or ())
    return next((lane for lane in lanes if getattr(lane, "name", "") == LANE_FASTEMBED), None) or (
        lanes[0] if lanes else None
    )


def _cache_key(lane: Any, documents: Sequence[str]) -> str:
    lane_id = str(getattr(lane, "fingerprint", "") or getattr(lane, "name", "unknown"))
    digest = hashlib.sha256()
    digest.update(lane_id.encode("utf-8"))
    for document in documents:
        digest.update(b"\0")
        digest.update(document.encode("utf-8", errors="replace"))
    return digest.hexdigest()


def _document_vectors(lane: Any, documents: Sequence[str]) -> List[List[float]]:
    key = _cache_key(lane, documents)
    with _cache_lock:
        cached = _corpus_cache.get(key)
        if cached is not None:
            _corpus_cache.move_to_end(key)
            return cached

    vectors = [list(vector) for vector in lane.encode(documents)]
    with _cache_lock:
        _corpus_cache[key] = vectors
        _corpus_cache.move_to_end(key)
        while len(_corpus_cache) > _CACHE_LIMIT:
            _corpus_cache.popitem(last=False)
    return vectors


def semantic_skill_scores(query: str, skills: Sequence[Dict[str, Any]]) -> Dict[int, float]:
    """Return cosine-like scores keyed by input position, or ``{}`` on fallback."""
    if not query.strip() or not skills:
        return {}
    try:
        # This accessor has no initialization side effect. Startup owns model
        # loading; foreground skill matching remains fast and deterministic.
        from src.tool_index import get_ready_tool_index

        index = get_ready_tool_index()
        if index is None:
            return {}
        lane = _choose_lane(index)
        if lane is None:
            return {}

        documents = [_semantic_text(skill) for skill in skills]
        vectors = _document_vectors(lane, documents)
        query_vectors = lane.encode([query[:4000]])
        if not query_vectors:
            return {}
        query_vector = list(query_vectors[0])

        scores: Dict[int, float] = {}
        for index_position, vector in enumerate(vectors):
            if len(vector) != len(query_vector) or not vector:
                continue
            # EmbeddingLane.encode requests normalized vectors, so their dot
            # product is cosine similarity without another numerical dependency.
            score = sum(float(left) * float(right) for left, right in zip(query_vector, vector))
            scores[index_position] = max(-1.0, min(1.0, score))
        return scores
    except Exception as exc:
        logger.debug("Semantic skill ranking unavailable; using lexical fallback: %s", exc)
        return {}



def learned_skill_quality_scores(training_skills, candidate_skills):
    """Predict skill audit quality from owner-scoped version-2 audit outcomes."""
    if not training_skills or not candidate_skills:
        return {}
    try:
        import numpy as np
        from src.tool_index import get_ready_tool_index
        from src.neural_network import NeuralNetworkClassifier
        index = get_ready_tool_index()
        lane = _choose_lane(index) if index is not None else None
        if lane is None:
            return {}
        candidate_owners = {str(skill.get("owner") or "") for skill in candidate_skills}
        if len(candidate_owners) != 1:
            return {}
        target_owner = next(iter(candidate_owners))
        positive_skills, negative_skills = [], []
        for skill in training_skills:
            if str(skill.get("owner") or "") != target_owner:
                continue
            try:
                audit_version = int(skill.get("audit_version") or 0)
            except (TypeError, ValueError):
                continue
            if audit_version != 2:
                continue
            baseline = str(skill.get("baseline_verdict") or "").strip().lower()
            if baseline not in {"better", "same", "worse"}:
                continue
            verdict = str(skill.get("audit_verdict") or "").strip().lower()
            if verdict == "pass":
                positive_skills.append(skill)
            elif verdict in {"fail", "needs_work"}:
                negative_skills.append(skill)
        if len(positive_skills) < 4 or len(negative_skills) < 4:
            return {}
        # Balance the observed classes and bound per-request training cost.
        sample_count = min(len(positive_skills), len(negative_skills), 128)
        sampler = np.random.default_rng(73)
        positive_indices = sampler.choice(len(positive_skills), sample_count, replace=False)
        negative_indices = sampler.choice(len(negative_skills), sample_count, replace=False)
        labelled = ([(positive_skills[int(i)], 1) for i in positive_indices] +
                    [(negative_skills[int(i)], 0) for i in negative_indices])
        sampler.shuffle(labelled)
        training_texts = [_semantic_text(skill) for skill, _ in labelled]
        labels = [label for _, label in labelled]
        digest = hashlib.sha256()
        digest.update(target_owner.encode("utf-8"))
        digest.update(str(getattr(lane, "fingerprint", lane.name)).encode("utf-8"))
        for document, label in zip(training_texts, labels):
            digest.update(b'\\0')
            digest.update(document.encode('utf-8', errors='replace'))
            digest.update(bytes([label]))
        cache_key = digest.hexdigest()
        with _cache_lock:
            model = _quality_model_cache.get(cache_key)
            if model is not None:
                _quality_model_cache.move_to_end(cache_key)
        if model is None:
            vectors = np.asarray(_document_vectors(lane, training_texts), dtype=np.float64)
            if vectors.ndim != 2 or not np.isfinite(vectors).all():
                return {}
            model = NeuralNetworkClassifier(vectors.shape[1], (32, 16), 2,
                                            learning_rate=0.003, seed=73)
            model.fit(vectors, np.asarray(labels, dtype=np.int64),
                      epochs=80, batch_size=min(16, len(labels)))
            with _cache_lock:
                _quality_model_cache[cache_key] = model
                _quality_model_cache.move_to_end(cache_key)
                while len(_quality_model_cache) > 8:
                    _quality_model_cache.popitem(last=False)
        candidate_texts = [_semantic_text(skill) for skill in candidate_skills]
        candidate_vectors = np.asarray(_document_vectors(lane, candidate_texts), dtype=np.float64)
        probabilities = model.predict_proba(candidate_vectors)
        return {i: float(probabilities[i, 1]) for i in range(len(candidate_skills))}
    except Exception as exc:
        logger.debug('Learned skill-quality ranking unavailable: %s', exc)
        return {}


def reset_skill_quality_cache():
    """Clear cached learned quality models after audit-data changes."""
    with _cache_lock:
        _quality_model_cache.clear()

def reset_skill_index_cache() -> None:
    """Clear process-local vectors after embedding configuration changes/tests."""
    with _cache_lock:
        _corpus_cache.clear()
        _quality_model_cache.clear()
