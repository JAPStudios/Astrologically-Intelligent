"""Documents (RAG): an uploaded file is chunked, indexed and then listed.

The app requirements pin `chromadb-client`; the ChromaDB server is a
separate install. The release-smoke CI job installs the matching pinned
server, requires its health endpoint to answer before app boot, then
fails rather than skips if the upload route still reports an unavailable
vector store. Local smoke runs without a server retain the explanatory
SKIP behavior.
"""
from __future__ import annotations

import os

import pytest

PERSONAL_PATH = "/api/personal"
UPLOAD_PATH = "/api/personal/upload"

# The route uniquifies the stored name and lists it under the owner's
# upload dir, so assertions match on the stem rather than the filename.
STEM = "odysseus-smoke-corpus"
FILENAME = f"{STEM}.txt"
CONTENT = (
    "The release smoke suite indexed this file. "
    "It exists so the retrieval path has something deterministic to chunk."
)
# The route's own 503 text when no vector store answers.
UNAVAILABLE_MARKER = "RAG system is not available"


def test_an_uploaded_file_is_indexed_and_listed(client):
    response = client.post(UPLOAD_PATH,
                           files={"files": (FILENAME, CONTENT.encode("utf-8"), "text/plain")},
                           timeout=180)
    if response.status_code == 503 and UNAVAILABLE_MARKER in response.text:
        reason = (
            "no vector service reachable, so indexing is unavailable. "
            "requirements.txt pins chromadb-client, not the server; install "
            "chromadb in the venv and re-run to cover this area."
        )
        if os.getenv("ODYSSEUS_REQUIRE_CHROMA") == "1":
            pytest.fail(reason)
        pytest.skip(reason)
    assert response.status_code == 200, response.text
    body = response.json()
    try:
        assert body.get("indexed_count", 0) > 0, f"nothing was indexed: {body}"
        assert body.get("failed_count", 1) == 0, f"a chunk failed to index: {body}"
        assert FILENAME in (body.get("uploaded") or []), body

        listed = client.get(PERSONAL_PATH)
        assert listed.status_code == 200, listed.text
        names = [str(f.get("name")) for f in listed.json().get("files") or []]
        assert any(STEM in name for name in names), names
    finally:
        listed = client.get(PERSONAL_PATH).json().get("files") or []
        for entry in listed:
            if STEM in str(entry.get("name")):
                client.request("DELETE", "/api/personal/file",
                               params={"filepath": entry.get("path")})
