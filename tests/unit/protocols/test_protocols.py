# import hashlib
# import sys
# from pathlib import Path
#
# import pytest
#
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
#
# # from space import protocols
#
#
# @pytest.fixture(autouse=True)
# def isolate_db(tmp_path, monkeypatch):
#     db_path = tmp_path / "protocols.db"
#     monkeypatch.setattr(protocols, "DB_PATH", db_path, raising=False)
#     if db_path.exists():
#         db_path.unlink()
#     yield
#     if db_path.exists():
#         db_path.unlink()
#
#
# def test_track_prefers_latest_hash():
#     protocols.track("space", "first version")
#     protocols.track("space", "second version")
#
#     latest_hash = hashlib.sha256(b"second version").hexdigest()[:16]
#
#     assert protocols.get_current_hash("space") == latest_hash
#
#     entries = protocols.list_protocols()
#     assert len(entries) == 1
#     name, stored_hash, created_at = entries[0]
#     assert name == "space"
#     assert stored_hash == latest_hash
#     assert isinstance(created_at, int)
#     assert created_at > 0
#
#
# def test_track_is_idempotent_for_identical_content():
#     content = "stable version"
#     protocols.track("bridge", content)
#     protocols.track("bridge", content)
#
#     expected_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
#     records = protocols.list_protocols()
#
#     assert len(records) == 1
#     assert records[0][0] == "bridge"
#     assert records[0][1] == expected_hash
