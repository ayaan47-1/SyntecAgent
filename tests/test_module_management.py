"""
Test suite for module management (agentic CRUD system).
Tests SQLite storage, CRUD operations, and REST API endpoints.
"""

import pytest
import sys
import os
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app2 import app, limiter


@pytest.fixture
def client():
    """Flask test client with rate limiting disabled"""
    app.config["TESTING"] = True
    limiter.enabled = False
    with app.test_client() as client:
        yield client
    limiter.enabled = True


@pytest.fixture
def temp_modules_db(tmp_path):
    """Use a temporary SQLite DB for each test."""
    import agent.db as agent_db

    db_path = str(tmp_path / "test_classifications.db")
    with patch("agent.db._DB_PATH", db_path):
        # Close any existing thread-local connection so get_db() reopens with the new path
        if hasattr(agent_db._local, "conn") and agent_db._local.conn is not None:
            try:
                agent_db._local.conn.close()
            except Exception:
                pass
        agent_db._local.__dict__.clear()
        from agent.db import init_db
        init_db()
        yield db_path
        # Cleanup
        if hasattr(agent_db._local, "conn") and agent_db._local.conn is not None:
            try:
                agent_db._local.conn.close()
            except Exception:
                pass
        agent_db._local.__dict__.clear()


class TestModuleCRUD:
    """Test CRUD functions directly."""

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_add_module_success(self, mock_get_emb, mock_collection, temp_modules_db):
        import agent.db as agent_db
        from agent.crud import add_module

        result = add_module("Foundation System", "FND-123", "Load-bearing foundation")
        assert result["success"] is True
        assert result["code"] == "FND-123"

        conn = agent_db.get_db()
        row = conn.execute(
            "SELECT * FROM classifications WHERE name = 'Foundation System'"
        ).fetchone()
        assert row is not None
        assert row["code"] == "FND-123"
        assert row["description"] == "Load-bearing foundation"

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_add_module_duplicate(self, mock_get_emb, mock_collection, temp_modules_db):
        from agent.crud import add_module

        add_module("Foundation System", "FND-123")
        result = add_module("foundation system", "FND-456")
        assert result["success"] is False
        assert "already exists" in result["error"]

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_get_module_found(self, mock_get_emb, mock_collection, temp_modules_db):
        from agent.crud import add_module, get_module

        add_module("Foundation System", "FND-123")
        result = get_module("Foundation System")
        assert result["found"] is True
        assert result["code"] == "FND-123"

    def test_get_module_not_found(self, temp_modules_db):
        from agent.crud import get_module

        result = get_module("Nonexistent Module")
        assert result["found"] is False

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_get_module_case_insensitive(
        self, mock_get_emb, mock_collection, temp_modules_db
    ):
        from agent.crud import add_module, get_module

        add_module("Foundation System", "FND-123")
        result = get_module("FOUNDATION SYSTEM")
        assert result["found"] is True

    def test_list_modules_empty(self, temp_modules_db):
        from agent.crud import list_modules

        result = list_modules()
        assert result["count"] == 0
        assert result["modules"] == []

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_list_modules_populated(
        self, mock_get_emb, mock_collection, temp_modules_db
    ):
        from agent.crud import add_module, list_modules

        add_module("Module A", "MOD-001")
        add_module("Module B", "MOD-002")
        result = list_modules()
        assert result["count"] == 2

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_update_module_success(self, mock_get_emb, mock_collection, temp_modules_db):
        from agent.crud import add_module, update_module

        add_module("Foundation System", "FND-123")
        result = update_module("Foundation System", new_code="FND-456")
        assert result["success"] is True
        assert result["old_code"] == "FND-123"
        assert result["new_code"] == "FND-456"

    def test_update_module_not_found(self, temp_modules_db):
        from agent.crud import update_module

        result = update_module("Nonexistent", new_code="X")
        assert result["success"] is False

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_delete_module_success(self, mock_get_emb, mock_collection, temp_modules_db):
        from agent.crud import add_module, delete_module

        add_module("Foundation System", "FND-123")
        result = delete_module("Foundation System")
        assert result["success"] is True
        assert result["code"] == "FND-123"

    def test_delete_module_not_found(self, temp_modules_db):
        from agent.crud import delete_module

        result = delete_module("Nonexistent")
        assert result["success"] is False

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_list_category(self, mock_get_emb, mock_collection, temp_modules_db):
        from agent.crud import add_module, list_category

        add_module("Type S Mortar", "04 05 13.A0", "Standard mortar")
        add_module("Type N Mortar", "04 05 13.A1", "Normal mortar")
        add_module("Concrete Block", "04 22 00.A0", "CMU block")

        result = list_category("04 05 13")
        assert result["count"] == 2
        assert result["prefix"] == "04 05 13"
        codes = {e["code"] for e in result["entries"]}
        assert "04 05 13.A0" in codes
        assert "04 05 13.A1" in codes
        assert "04 22 00.A0" not in codes

    def test_list_category_empty(self, temp_modules_db):
        from agent.crud import list_category

        result = list_category("99 99 99")
        assert result["count"] == 0
        assert result["entries"] == []

    # ------------------------------------------------------------------
    # Token-cap tests
    # ------------------------------------------------------------------

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_list_modules_capped_at_50(self, mock_emb, mock_coll, temp_modules_db):
        """list_modules returns at most 50 rows even when 60 exist."""
        from agent.crud import add_module, list_modules

        for i in range(60):
            add_module(f"Cap Module {i:03d}", f"CAP-{i:03d}")

        result = list_modules()
        assert result["returned"] == 50
        assert result["count"] == 60
        assert result["truncated"] is True

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_list_modules_hint_when_truncated(self, mock_emb, mock_coll, temp_modules_db):
        """When truncated, the hint mentions 'list_category'."""
        from agent.crud import add_module, list_modules

        for i in range(60):
            add_module(f"Hint Module {i:03d}", f"HNT-{i:03d}")

        result = list_modules()
        assert "list_category" in result.get("hint", "")

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_list_modules_no_truncation_flag_under_limit(
        self, mock_emb, mock_coll, temp_modules_db
    ):
        """With fewer than 50 rows, 'truncated' key is absent from result."""
        from agent.crud import add_module, list_modules

        add_module("Alpha", "ALP-001")
        add_module("Beta", "ALP-002")
        add_module("Gamma", "ALP-003")

        result = list_modules()
        assert "truncated" not in result

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_list_category_capped_at_100(self, mock_emb, mock_coll, temp_modules_db):
        """list_category returns at most 100 rows for a prefix with 110 matches."""
        from agent.crud import add_module, list_category

        for i in range(110):
            add_module(f"TST Module {i:03d}", f"TST.{i:03d}")

        result = list_category("TST")
        assert result["returned"] == 100
        assert result["truncated"] is True

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_list_category_count_is_total_not_returned(
        self, mock_emb, mock_coll, temp_modules_db
    ):
        """count reflects the true total (110), not the capped returned value (100)."""
        from agent.crud import add_module, list_category

        for i in range(110):
            add_module(f"CNT Module {i:03d}", f"CNT.{i:03d}")

        result = list_category("CNT")
        assert result["count"] == 110
        assert result["returned"] == 100

    # ------------------------------------------------------------------
    # P0-1+2: SQLite/ChromaDB atomicity tests
    # ------------------------------------------------------------------

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_add_module_chromadb_failure_rolls_back(
        self, mock_get_emb, mock_collection, temp_modules_db
    ):
        """add_module with ChromaDB upsert failure → success=False + no SQLite row."""
        import agent.db as agent_db
        from agent.crud import add_module

        mock_collection.upsert.side_effect = Exception("ChromaDB unavailable")

        result = add_module("Rollback Module", "RB-001", "Test rollback")
        assert result["success"] is False

        conn = agent_db.get_db()
        row = conn.execute(
            "SELECT * FROM classifications WHERE name = 'Rollback Module'"
        ).fetchone()
        assert row is None

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_update_module_chromadb_failure_rolls_back(
        self, mock_get_emb, mock_collection, temp_modules_db
    ):
        """update_module with ChromaDB upsert failure → success=False + original code unchanged."""
        import agent.db as agent_db
        from agent.crud import add_module, update_module

        # Add successfully (upsert doesn't raise by default)
        add_module("Update Rollback", "UR-001", "Test")

        # Now make upsert fail for the update
        mock_collection.upsert.side_effect = Exception("ChromaDB unavailable")

        result = update_module("Update Rollback", new_code="UR-999")
        assert result["success"] is False

        conn = agent_db.get_db()
        row = conn.execute(
            "SELECT * FROM classifications WHERE name = 'Update Rollback'"
        ).fetchone()
        assert row["code"] == "UR-001"  # code unchanged

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_delete_module_chromadb_failure_rolls_back(
        self, mock_get_emb, mock_collection, temp_modules_db
    ):
        """delete_module with ChromaDB delete failure → success=False + row still exists."""
        import agent.db as agent_db
        from agent.crud import add_module, delete_module

        add_module("Delete Rollback", "DR-001", "Test")

        mock_collection.delete.side_effect = Exception("ChromaDB unavailable")

        result = delete_module("Delete Rollback")
        assert result["success"] is False

        conn = agent_db.get_db()
        row = conn.execute(
            "SELECT * FROM classifications WHERE name = 'Delete Rollback'"
        ).fetchone()
        assert row is not None  # row still exists

    # ------------------------------------------------------------------
    # P0-5: Race condition — rowcount check
    # ------------------------------------------------------------------

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_update_module_row_deleted_concurrently(
        self, mock_get_emb, mock_collection, temp_modules_db
    ):
        """update_module after row is externally deleted → success=False."""
        import agent.db as agent_db
        from agent.crud import add_module, update_module

        add_module("Concurrent Delete", "CD-001")

        # Simulate concurrent deletion by deleting the row directly
        conn = agent_db.get_db()
        conn.execute(
            "DELETE FROM classifications WHERE name=?", ("Concurrent Delete",)
        )
        conn.commit()

        result = update_module("Concurrent Delete", new_code="CD-999")
        assert result["success"] is False


class TestListCategoryWildcard:
    """Test that LIKE wildcards in category_prefix are properly escaped."""

    def test_underscore_not_treated_as_wildcard(self, temp_modules_db):
        """'04_05_13' must NOT match '04 05 13.A1' or '04x05x13.A1'."""
        import agent.db as agent_db
        from agent.crud import list_category

        conn = agent_db.get_db()
        now = "2026-01-01T00:00:00+00:00"
        conn.execute(
            "INSERT INTO classifications (code, name, source, created_at, updated_at) VALUES (?, ?, 'test', ?, ?)",
            ("04 05 13.A1", "Space Code", now, now),
        )
        conn.execute(
            "INSERT INTO classifications (code, name, source, created_at, updated_at) VALUES (?, ?, 'test', ?, ?)",
            ("04x05x13.A1", "X Code", now, now),
        )
        conn.commit()

        result = list_category("04_05_13")
        assert result["count"] == 0

    def test_percent_not_treated_as_wildcard(self, temp_modules_db):
        """'AA%' prefix must NOT match 'AA.B1'."""
        import agent.db as agent_db
        from agent.crud import list_category

        conn = agent_db.get_db()
        now = "2026-01-01T00:00:00+00:00"
        conn.execute(
            "INSERT INTO classifications (code, name, source, created_at, updated_at) VALUES (?, ?, 'test', ?, ?)",
            ("AA.B1", "AA B1", now, now),
        )
        conn.commit()

        result = list_category("AA%")
        assert result["count"] == 0

    def test_normal_prefix_still_works(self, temp_modules_db):
        """Normal prefix '04 05 13' matches exactly two codes under that prefix."""
        import agent.db as agent_db
        from agent.crud import list_category

        conn = agent_db.get_db()
        now = "2026-01-01T00:00:00+00:00"
        conn.execute(
            "INSERT INTO classifications (code, name, source, created_at, updated_at) VALUES (?, ?, 'test', ?, ?)",
            ("04 05 13.A1", "A1 Mortar", now, now),
        )
        conn.execute(
            "INSERT INTO classifications (code, name, source, created_at, updated_at) VALUES (?, ?, 'test', ?, ?)",
            ("04 05 13.A2", "A2 Mortar", now, now),
        )
        conn.commit()

        result = list_category("04 05 13")
        assert result["count"] == 2


class TestModuleRESTAPI:
    """Test REST API endpoints."""

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_api_add_and_list(
        self, mock_get_emb, mock_collection, client, temp_modules_db
    ):
        response = client.post(
            "/api/modules",
            json={
                "module_name": "Test Module",
                "code": "TST-001",
                "description": "A test module",
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True

        response = client.get("/api/modules")
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_api_get_module(
        self, mock_get_emb, mock_collection, client, temp_modules_db
    ):
        client.post(
            "/api/modules", json={"module_name": "Test Module", "code": "TST-001"}
        )
        response = client.get("/api/modules/Test Module")
        assert response.status_code == 200
        assert response.get_json()["found"] is True

    def test_api_get_module_not_found(self, client, temp_modules_db):
        response = client.get("/api/modules/Nonexistent")
        assert response.status_code == 404

    def test_api_add_module_missing_fields(self, client, temp_modules_db):
        response = client.post("/api/modules", json={"module_name": "Test"})
        assert response.status_code == 400

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_api_delete_module(
        self, mock_get_emb, mock_collection, client, temp_modules_db
    ):
        client.post(
            "/api/modules", json={"module_name": "Test Module", "code": "TST-001"}
        )
        response = client.delete("/api/modules/Test Module?confirm=true")
        assert response.status_code == 200
        assert response.get_json()["success"] is True

    # ------------------------------------------------------------------
    # P0-6: Confirmation gate for PUT/DELETE
    # ------------------------------------------------------------------

    def test_delete_without_confirm_returns_409(self, client, temp_modules_db):
        """DELETE without ?confirm=true → 409 with pending_action."""
        response = client.delete("/api/modules/SomeModule")
        assert response.status_code == 409
        data = response.get_json()
        assert "pending_action" in data
        assert data["pending_action"]["type"] == "delete_module"

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_delete_with_confirm_executes(
        self, mock_get_emb, mock_collection, client, temp_modules_db
    ):
        """DELETE with ?confirm=true → 200 and module removed."""
        import agent.db as agent_db

        client.post(
            "/api/modules",
            json={"module_name": "Delete Me", "code": "DM-001"},
        )
        response = client.delete("/api/modules/Delete Me?confirm=true")
        assert response.status_code == 200
        assert response.get_json()["success"] is True

        conn = agent_db.get_db()
        row = conn.execute(
            "SELECT * FROM classifications WHERE name = 'Delete Me'"
        ).fetchone()
        assert row is None

    def test_update_without_confirm_returns_409(self, client, temp_modules_db):
        """PUT without ?confirm=true → 409 with pending_action."""
        response = client.put(
            "/api/modules/SomeModule", json={"new_code": "NEW-001"}
        )
        assert response.status_code == 409
        data = response.get_json()
        assert "pending_action" in data
        assert data["pending_action"]["type"] == "update_module"

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_update_with_confirm_executes(
        self, mock_get_emb, mock_collection, client, temp_modules_db
    ):
        """PUT with ?confirm=true → 200 and code updated."""
        import agent.db as agent_db

        client.post(
            "/api/modules",
            json={"module_name": "Update Me", "code": "UM-001"},
        )
        response = client.put(
            "/api/modules/Update Me?confirm=true",
            json={"new_code": "UM-999"},
        )
        assert response.status_code == 200
        assert response.get_json()["success"] is True

        conn = agent_db.get_db()
        row = conn.execute(
            "SELECT * FROM classifications WHERE name = 'Update Me'"
        ).fetchone()
        assert row["code"] == "UM-999"

    @patch("agent.chromadb_sync._collection")
    @patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
    def test_api_list_category(
        self, mock_get_emb, mock_collection, client, temp_modules_db
    ):
        client.post(
            "/api/modules",
            json={"module_name": "Type S Mortar", "code": "04 05 13.A0"},
        )
        client.post(
            "/api/modules",
            json={"module_name": "Type N Mortar", "code": "04 05 13.A1"},
        )
        response = client.get("/api/modules/category/04 05 13")
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 2
