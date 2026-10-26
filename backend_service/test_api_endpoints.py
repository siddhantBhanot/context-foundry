#!/usr/bin/env python3
"""
Integration verification test suite for backend_service.
Executes end-to-end tests across all versioned /api/v1 routes,
validating JWT authentication, user-scoped conversation isolation,
SQLite persistence, feedback, and error handling.
"""

import os
from pathlib import Path
import sys
import unittest

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from starlette.testclient import TestClient
from backend_service.app.main import app
from backend_service.app.infrastructure.configuration import settings as settings_module


class TestBackendServiceAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_db = _project_root / "backend_service" / "data" / "test_api.db"
        if test_db.exists():
            test_db.unlink()
        os.environ["DATABASE_PATH"] = str(test_db)
        os.environ["RAG_CLIENT_MODE"] = "mock"  # Fast mock adapter for automated test suite

        # Reset cached settings and DB
        settings_module._settings = None
        from backend_service.app.infrastructure.persistence import database as db_module
        db_module._db = None

        cls._client_cm = TestClient(app)
        cls.client = cls._client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._client_cm.__exit__(None, None, None)

    def test_01_health_check(self):
        """Test GET /api/v1/health returns healthy status and DB responsiveness."""
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "backend_service")
        self.assertEqual(data["database"], "healthy")
        self.assertIn("X-Request-ID", response.headers)

    def test_02_auth_signup_and_login(self):
        """Test user signup, duplicate detection, and login issuing valid JWT tokens."""
        # 1. Signup
        signup_resp = self.client.post(
            "/api/v1/auth/signup",
            json={
                "email": "alice@demo.io",
                "password": "securepassword123",
                "name": "Alice Engineer",
            },
        )
        self.assertEqual(signup_resp.status_code, 201)
        signup_data = signup_resp.json()
        self.assertIn("access_token", signup_data)
        self.assertEqual(signup_data["user"]["email"], "alice@demo.io")
        self.assertEqual(signup_data["user"]["name"], "Alice Engineer")

        # 2. Duplicate signup fails
        dup_resp = self.client.post(
            "/api/v1/auth/signup",
            json={
                "email": "alice@demo.io",
                "password": "securepassword123",
                "name": "Alice Duplicate",
            },
        )
        self.assertEqual(dup_resp.status_code, 422)

        # 3. Login
        login_resp = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "alice@demo.io",
                "password": "securepassword123",
            },
        )
        self.assertEqual(login_resp.status_code, 200)
        login_data = login_resp.json()
        self.assertIn("access_token", login_data)

        # 4. Check /auth/me with Bearer token
        token = login_data["access_token"]
        me_resp = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()["email"], "alice@demo.io")

    def test_03_unauthenticated_requests_fail(self):
        """Test protected routes reject requests without valid Bearer tokens with 401."""
        # 1. Unauthenticated query
        resp_query = self.client.post("/api/v1/query", json={"query": "hello"})
        self.assertEqual(resp_query.status_code, 401)
        self.assertEqual(resp_query.json()["code"], "AUTHENTICATION_FAILED")

        # 2. Unauthenticated conversations
        resp_conv = self.client.get("/api/v1/conversations")
        self.assertEqual(resp_conv.status_code, 401)

        # 3. Unauthenticated knowledge trigger
        resp_knowledge = self.client.post("/api/v1/knowledge", json={"service": "income-assessment-service"})
        self.assertEqual(resp_knowledge.status_code, 401)

    def test_04_query_execution_and_persistence(self):
        """Test POST /api/v1/query with JWT creates conversation and returns citations."""
        # Login Alice
        login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "alice@demo.io", "password": "securepassword123"},
        ).json()
        auth_headers = {"Authorization": f"Bearer {login['access_token']}"}

        payload = {
            "query": "What is Zenith and what is it used for?",
            "service": "income-assessment-service",
            "top_k": 5,
        }
        response = self.client.post("/api/v1/query", json=payload, headers=auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("conversation_id", data)
        self.assertIn("message_id", data)
        self.assertIn("answer", data)
        self.assertIn("sources", data)

        cid = data["conversation_id"]

        # Verify conversation history from SQLite
        conv_resp = self.client.get(f"/api/v1/conversations/{cid}", headers=auth_headers)
        self.assertEqual(conv_resp.status_code, 200)
        conv_data = conv_resp.json()
        self.assertEqual(conv_data["id"], cid)
        self.assertEqual(len(conv_data["messages"]), 2)  # 1 user + 1 assistant

    def test_05_user_conversation_isolation(self):
        """Test strict user-scoped conversation isolation across different users."""
        # 1. Alice creates a conversation
        alice_login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "alice@demo.io", "password": "securepassword123"},
        ).json()
        alice_headers = {"Authorization": f"Bearer {alice_login['access_token']}"}

        alice_query = self.client.post(
            "/api/v1/query",
            json={"query": "Alice private architecture question"},
            headers=alice_headers,
        ).json()
        alice_cid = alice_query["conversation_id"]

        # 2. Register Bob
        bob_signup = self.client.post(
            "/api/v1/auth/signup",
            json={
                "email": "bob@demo.io",
                "password": "bobpassword123",
                "name": "Bob Reviewer",
            },
        ).json()
        bob_headers = {"Authorization": f"Bearer {bob_signup['access_token']}"}

        # 3. Bob lists conversations -> Bob should see ZERO conversations
        bob_list = self.client.get("/api/v1/conversations", headers=bob_headers)
        self.assertEqual(bob_list.status_code, 200)
        bob_convs = bob_list.json()
        self.assertEqual(len(bob_convs), 0, "Bob must not see Alice's conversations")

        # 4. Bob attempts to access Alice's conversation by ID -> 404 (isolation enforced)
        bob_get = self.client.get(f"/api/v1/conversations/{alice_cid}", headers=bob_headers)
        self.assertEqual(bob_get.status_code, 404)

        # 5. Bob creates his own conversation
        bob_query = self.client.post(
            "/api/v1/query",
            json={"query": "Bob query regarding KYC"},
            headers=bob_headers,
        ).json()
        bob_cid = bob_query["conversation_id"]

        # 6. Bob now sees only 1 conversation
        bob_list_after = self.client.get("/api/v1/conversations", headers=bob_headers).json()
        self.assertEqual(len(bob_list_after), 1)
        self.assertEqual(bob_list_after[0]["id"], bob_cid)

        # 7. Alice lists conversations -> Alice sees only Alice's conversations
        alice_list = self.client.get("/api/v1/conversations", headers=alice_headers).json()
        alice_ids = [c["id"] for c in alice_list]
        self.assertIn(alice_cid, alice_ids)
        self.assertNotIn(bob_cid, alice_ids)

    def test_06_knowledge_ingestion_with_auth(self):
        """Test POST /api/v1/knowledge triggers ingestion job when authenticated."""
        alice_login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "alice@demo.io", "password": "securepassword123"},
        ).json()
        alice_headers = {"Authorization": f"Bearer {alice_login['access_token']}"}

        response = self.client.post(
            "/api/v1/knowledge",
            json={"service": "income-assessment-service"},
            headers=alice_headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("job_id", data)
        self.assertEqual(data["status"], "completed")

    def test_07_error_handling_and_request_id(self):
        """Test error handling produces standardized JSON schema with request_id."""
        # 1. 422 on invalid request body
        bad_response = self.client.post("/api/v1/auth/signup", json={"email": "invalid"})
        self.assertEqual(bad_response.status_code, 422)
        err_data = bad_response.json()
        self.assertIn("code", err_data)
        self.assertIn("message", err_data)
        self.assertIn("request_id", err_data)
        self.assertIn("X-Request-ID", bad_response.headers)
        self.assertEqual(err_data["request_id"], bad_response.headers["X-Request-ID"])

    def test_08_conversation_sharing_and_fork_on_reply(self):
        """Test conversation sharing link generation and automatic fork-on-reply."""
        # 1. Alice creates a multi-turn conversation
        alice_login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "alice@demo.io", "password": "securepassword123"},
        ).json()
        alice_headers = {"Authorization": f"Bearer {alice_login['access_token']}"}

        q1 = self.client.post(
            "/api/v1/query",
            json={"query": "Alice original question on income assessment"},
            headers=alice_headers,
        ).json()
        alice_cid = q1["conversation_id"]

        q2 = self.client.post(
            "/api/v1/query",
            json={"query": "Alice follow up question", "conversation_id": alice_cid},
            headers=alice_headers,
        ).json()
        self.assertEqual(q2["conversation_id"], alice_cid)

        # 2. Alice generates a share token
        share_resp = self.client.post(
            f"/api/v1/conversations/{alice_cid}/share",
            headers=alice_headers,
        )
        self.assertEqual(share_resp.status_code, 200)
        share_data = share_resp.json()
        share_token = share_data["share_token"]
        self.assertTrue(len(share_token) > 0)
        self.assertIn(share_token, share_data["share_url"])

        # 3. Unauthenticated request to shared conversation must fail with 401
        unauth_resp = self.client.get(f"/api/v1/shared/{share_token}")
        self.assertEqual(unauth_resp.status_code, 401)

        # 4. Bob (authenticated) can view Alice's shared conversation
        bob_login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "bob@demo.io", "password": "bobpassword123"},
        ).json()
        bob_headers = {"Authorization": f"Bearer {bob_login['access_token']}"}

        bob_view = self.client.get(f"/api/v1/shared/{share_token}", headers=bob_headers)
        self.assertEqual(bob_view.status_code, 200)
        bob_view_data = bob_view.json()
        self.assertEqual(bob_view_data["id"], alice_cid)
        self.assertFalse(bob_view_data["is_owner"], "Bob is not the owner of Alice's shared thread")
        self.assertEqual(len(bob_view_data["messages"]), 4, "Should have 2 turns = 4 messages")

        # 5. Alice views her shared conversation -> is_owner is True
        alice_view = self.client.get(f"/api/v1/shared/{share_token}", headers=alice_headers)
        self.assertEqual(alice_view.status_code, 200)
        self.assertTrue(alice_view.json()["is_owner"])

        # 6. Alice replies to her own shared thread -> continues normally (no fork)
        alice_reply = self.client.post(
            "/api/v1/query",
            json={"query": "Alice 3rd query on same thread", "share_token": share_token},
            headers=alice_headers,
        ).json()
        self.assertEqual(alice_reply["conversation_id"], alice_cid)
        self.assertFalse(alice_reply["forked"])

        # Alice's conversation now has 6 messages
        alice_conv_after = self.client.get(f"/api/v1/conversations/{alice_cid}", headers=alice_headers).json()
        self.assertEqual(len(alice_conv_after["messages"]), 6)

        # 7. Bob replies to Alice's shared thread -> FORK ON REPLY!
        bob_reply = self.client.post(
            "/api/v1/query",
            json={"query": "Bob branching question on this thread", "share_token": share_token},
            headers=bob_headers,
        ).json()
        bob_forked_cid = bob_reply["conversation_id"]

        self.assertNotEqual(bob_forked_cid, alice_cid, "Forked conversation must have a brand new session ID")
        self.assertTrue(bob_reply["forked"])
        self.assertEqual(bob_reply["forked_from"], alice_cid)

        # 8. Check Bob's forked conversation:
        # It must contain Alice's 6 previous messages + Bob's 1 prompt + 1 model reply = 8 messages
        bob_conv = self.client.get(f"/api/v1/conversations/{bob_forked_cid}", headers=bob_headers).json()
        self.assertEqual(len(bob_conv["messages"]), 8)
        self.assertEqual(bob_conv["forked_from"], alice_cid)
        self.assertEqual(bob_conv["messages"][-2]["content"], "Bob branching question on this thread")

        # 9. Verify Alice's original conversation is completely UNTOUCHED
        alice_check = self.client.get(f"/api/v1/conversations/{alice_cid}", headers=alice_headers).json()
        self.assertEqual(len(alice_check["messages"]), 6, "Alice's original thread must remain untouched")

        # 10. Bob sees the forked conversation in his list
        bob_list = self.client.get("/api/v1/conversations", headers=bob_headers).json()
        bob_cids = [c["id"] for c in bob_list]
        self.assertIn(bob_forked_cid, bob_cids)
        self.assertNotIn(alice_cid, bob_cids)

    def test_09_document_viewing_and_security_guardrails(self):
        """Test GET /api/v1/documents security guardrails (auth, traversal, extension whitelist)."""
        # 1. Unauthenticated request rejected
        unauth_resp = self.client.get(
            "/api/v1/documents",
            params={"service": "income-assessment-service", "file": "00-overview.md"},
        )
        self.assertEqual(unauth_resp.status_code, 401)

        # Login to get token
        login_resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "alice@demo.io", "password": "securepassword123"},
        ).json()
        headers = {"Authorization": f"Bearer {login_resp['access_token']}"}

        # 2. Valid markdown document viewing
        valid_resp = self.client.get(
            "/api/v1/documents",
            params={"service": "income-assessment-service", "file": "00-overview.md"},
            headers=headers,
        )
        self.assertEqual(valid_resp.status_code, 200)
        doc_data = valid_resp.json()
        self.assertEqual(doc_data["file"], "00-overview.md")
        self.assertEqual(doc_data["service"], "income-assessment-service")
        self.assertEqual(doc_data["content_type"], "text/markdown")
        self.assertGreater(doc_data["total_lines"], 0)
        self.assertGreater(doc_data["size_bytes"], 0)
        self.assertIn("Income Assessment", doc_data["content"])

        # 2b. Valid markdown document viewing with full absolute path from Qdrant citation
        abs_doc_resp = self.client.get(
            "/api/v1/documents",
            params={
                "service": "income-assessment-service",
                "file": "/Users/siddhantbhanot/Developer/context-foundry/rag_service/sample_data/income-assessment-service/01-architecture.md",
            },
            headers=headers,
        )
        self.assertEqual(abs_doc_resp.status_code, 200)
        abs_doc_data = abs_doc_resp.json()
        self.assertEqual(abs_doc_data["file"], "01-architecture.md")
        self.assertIn("Architecture", abs_doc_data["content"])

        # 3. Path traversal blocked with 403 Forbidden
        traversal_resp = self.client.get(
            "/api/v1/documents",
            params={"service": "income-assessment-service", "file": "../../etc/passwd"},
            headers=headers,
        )
        self.assertEqual(traversal_resp.status_code, 403)
        self.assertEqual(traversal_resp.json()["code"], "FORBIDDEN")

        # 4. Source code file blocked with 403 Forbidden (restricted to docs only)
        code_resp = self.client.get(
            "/api/v1/documents",
            params={"service": "income-assessment-service", "file": "FourWheelerPersonalAssessmentHandler.kt"},
            headers=headers,
        )
        self.assertEqual(code_resp.status_code, 403)
        self.assertEqual(code_resp.json()["code"], "FORBIDDEN")

        # 5. Non-existent markdown file returns 404
        not_found_resp = self.client.get(
            "/api/v1/documents",
            params={"service": "income-assessment-service", "file": "non_existent_doc.md"},
            headers=headers,
        )
        self.assertEqual(not_found_resp.status_code, 404)
        self.assertEqual(not_found_resp.json()["code"], "ENTITY_NOT_FOUND")

    def test_10_list_models(self):
        """Test GET /api/v1/models returns available models configured on the backend."""
        response = self.client.get("/api/v1/models")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("models", data)
        self.assertIn("default_model", data)
        self.assertTrue(len(data["models"]) > 0)
        default_found = any(m["id"] == data["default_model"] for m in data["models"])
        self.assertTrue(default_found)

    def test_11_query_with_model_override(self):
        """Test POST /api/v1/query with dynamic model selection generates response using chosen model."""
        # 1. Login user
        login_resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "alice@demo.io", "password": "securepassword123"},
        )
        self.assertEqual(login_resp.status_code, 200)
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Query with model="mock-llama-3"
        query_resp = self.client.post(
            "/api/v1/query",
            json={
                "query": "How does income assessment work?",
                "service": "income-assessment-service",
                "model": "mock-llama-3",
            },
            headers=headers,
        )
        self.assertEqual(query_resp.status_code, 200)
        data = query_resp.json()
        self.assertEqual(data["model"], "mock-llama-3")


if __name__ == "__main__":
    unittest.main(verbosity=2)


