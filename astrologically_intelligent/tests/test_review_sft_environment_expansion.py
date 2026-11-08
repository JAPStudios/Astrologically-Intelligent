import json

from scripts import review_sft_environment_expansion as review


def test_remove_trace_sessions_is_owner_file_scoped_and_atomic(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "TRACE_DIR", tmp_path)
    path = tmp_path / "owner.jsonl"
    rows = [
        {"session_id": "keep", "user": "a"},
        {"session_id": "reject", "user": "b"},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    assert review.remove_trace_sessions("owner", {"reject"}) == 1
    remaining = [json.loads(line) for line in path.read_text().splitlines()]
    assert [row["session_id"] for row in remaining] == ["keep"]


def test_trace_rows_selects_only_requested_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "TRACE_DIR", tmp_path)
    path = tmp_path / "owner.jsonl"
    path.write_text(
        json.dumps({"session_id": "one"}) + "\n" + json.dumps({"session_id": "two"}) + "\n"
    )
    assert review.trace_rows("owner", {"two"}) == [{"session_id": "two"}]

def test_trace_owner_cannot_escape_trace_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "TRACE_DIR", tmp_path)
    import pytest

    with pytest.raises(ValueError, match="invalid SFT trace owner identifier"):
        review.trace_rows("../../outside", {"session"})


def test_session_identifier_is_validated_before_trace_lookup_or_deletion(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "TRACE_DIR", tmp_path)
    import pytest

    with pytest.raises(ValueError, match="invalid SFT session identifier"):
        review.trace_rows("owner", {"../outside"})

    with pytest.raises(ValueError, match="invalid SFT session identifier"):
        review.remove_trace_sessions("owner", {"../outside"})


def test_live_session_deletion_rejects_unsafe_owner_before_network_access(monkeypatch):
    import pytest

    def forbidden_client():
        raise AssertionError("network client must not be created for an invalid owner")

    monkeypatch.setattr(review.httpx, "Client", forbidden_client)
    with pytest.raises(ValueError, match="invalid SFT trace owner identifier"):
        review.delete_live_sessions("http://127.0.0.1:7011", "password", {"../outside": {"session"}})

def test_trace_symlink_cannot_escape_trace_directory(tmp_path, monkeypatch):
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    outside = tmp_path / "outside.jsonl"
    outside.write_text(json.dumps({"session_id": "session"}) + "\\n", encoding="utf-8")
    (trace_dir / "owner.jsonl").symlink_to(outside)
    monkeypatch.setattr(review, "TRACE_DIR", trace_dir)

    import pytest

    with pytest.raises(ValueError, match="SFT trace path escapes its directory"):
        review.trace_rows("owner", {"session"})

    with pytest.raises(ValueError, match="SFT trace path escapes its directory"):
        review.remove_trace_sessions("owner", {"session"})

def test_review_rejects_one_session_assigned_to_multiple_owners():
    import pytest

    with pytest.raises(ValueError, match="assigned to multiple owners"):
        review._owner_session_map([
            {"session_id": "same-session", "owner": "owner-a"},
            {"session_id": "same-session", "owner": "owner-b"},
        ])
def test_owner_session_map_accepts_multiple_sessions_for_one_owner():
    assert review._owner_session_map([
        {"session_id": "session-one", "owner": "owner-a"},
        {"session_id": "session-two", "owner": "owner-a"},
    ]) == {"session-one": "owner-a", "session-two": "owner-a"}


def test_owner_session_map_rejects_invalid_session_identity():
    import pytest

    with pytest.raises(ValueError, match="invalid SFT session identifier"):
        review._owner_session_map([
            {"session_id": "../outside", "owner": "owner-a"},
        ])


def test_owner_session_map_rejects_invalid_owner_identity():
    import pytest

    with pytest.raises(ValueError, match="invalid SFT trace owner identifier"):
        review._owner_session_map([
            {"session_id": "session-one", "owner": "../outside"},
        ])
