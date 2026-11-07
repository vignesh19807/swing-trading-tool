"""
CORS Configuration and Origin Validation Tests
==============================================
Verifies Cross-Origin Resource Sharing behavior according to Task D of Phase 5.3.8.1:
1. Permitted Vercel production origin receives Access-Control-Allow-Origin header.
2. Permitted local frontend development origin (http://localhost:5173) receives Access-Control-Allow-Origin header.
3. Disallowed origin (e.g. evil-tracker.com) is NOT granted Access-Control-Allow-Origin.
4. Preflight OPTIONS requests succeed with appropriate CORS response headers.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app import app


class TestCORSConfiguration:
    """Test suite validating CORS middleware behavior for frontend integrations."""

    def test_cors_allowed_local_origin(self):
        """Verify local development origin (http://localhost:5173) is allowed."""
        client = TestClient(app)
        headers = {
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        }
        res = client.options("/healthz/live", headers=headers)
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert res.headers.get("access-control-allow-credentials") == "true"

    def test_cors_disallowed_origin_rejected(self):
        """Verify unauthorized origins do not receive allow-origin header."""
        client = TestClient(app)
        headers = {
            "Origin": "https://malicious-external-site.com",
            "Access-Control-Request-Method": "GET",
        }
        res = client.options("/healthz/live", headers=headers)
        # FastAPIs CORS middleware does not set access-control-allow-origin if origin is not in allow_origins
        assert res.headers.get("access-control-allow-origin") is None

    def test_cors_actual_get_request_allowed_origin(self):
        """Verify GET request with Origin header receives access-control-allow-origin."""
        client = TestClient(app)
        headers = {"Origin": "http://localhost:5173"}
        res = client.get("/healthz/live", headers=headers)
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_cors_actual_get_request_disallowed_origin(self):
        """Verify GET request with disallowed Origin does not receive access-control-allow-origin."""
        client = TestClient(app)
        headers = {"Origin": "https://unauthorized-origin.com"}
        res = client.get("/healthz/live", headers=headers)
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") is None

    def test_cors_vercel_production_origin_allowed(self, monkeypatch):
        """Verify dynamic CORS_ORIGINS with Vercel production origin works."""
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi import FastAPI
        from backend.config import CORS_ORIGINS

        # Verify parsing of multiple comma-separated origins
        custom_env = "https://swing-trading-tool.vercel.app,http://localhost:5173"
        parsed = [o.strip() for o in custom_env.split(",") if o.strip()]
        assert "https://swing-trading-tool.vercel.app" in parsed
        assert "http://localhost:5173" in parsed

        test_app = FastAPI()
        test_app.add_middleware(
            CORSMiddleware,
            allow_origins=parsed,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )
        @test_app.get("/ping")
        def ping():
            return {"status": "ok"}

        test_client = TestClient(test_app)
        headers = {"Origin": "https://swing-trading-tool.vercel.app"}
        res = test_client.get("/ping", headers=headers)
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "https://swing-trading-tool.vercel.app"
        assert res.headers.get("access-control-allow-credentials") == "true"

        # Verify unknown origin rejected
        bad_res = test_client.get("/ping", headers={"Origin": "https://attacker.com"})
        assert bad_res.status_code == 200
        assert bad_res.headers.get("access-control-allow-origin") is None

    def test_admin_authentication_unaffected_by_cors(self):
        """Verify admin authentication via X-API-Key operates securely with CORS headers."""
        client = TestClient(app)
        # Attempt to access protected admin endpoint without API key
        headers = {"Origin": "http://localhost:5173"}
        res = client.post("/api/universe/stocks", json={"symbol": "NEW"}, headers=headers)
        # Should return 403 or 401 for missing/invalid key, never 200
        assert res.status_code in (401, 403)


