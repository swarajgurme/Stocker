import json
import uuid

import pytest

from database import init_db
from services.report_service import ReportService


@pytest.fixture(autouse=True)
def _db():
    init_db()
    yield


@pytest.fixture
def client():
    from server import app

    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def register_and_login(client, email=None, password="testpassword123"):
    email = email or f"qa_{uuid.uuid4().hex[:8]}@test.com"
    r = client.post(
        "/api/auth/register",
        data=json.dumps(
            {"email": email, "password": password, "full_name": "QA User"}
        ),
        content_type="application/json",
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    payload = json.loads(r.get_data(as_text=True))
    tok = payload["data"]["access_token"]
    return email, password, tok


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("database") == "OK"
    assert "version" in body


def test_auth_me(client):
    _, _, tok = register_and_login(client)
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200


def test_inventory_root_alias(client):
    _, _, tok = register_and_login(client)
    r = client.get("/api/inventory", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    data = r.get_json()["data"]
    assert "inventory" in data


def test_forecast_history_alias(client):
    _, _, tok = register_and_login(client)
    r = client.get("/api/forecast/history", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200


def test_report_service_collect(client):
    svc = ReportService()
    data = svc._collect_report_data("executive_summary")
    assert "summary" in data
    assert "total_revenue" in data["summary"]


def test_register_rejects_admin_role(client):
    r = client.post(
        "/api/auth/register",
        data=json.dumps(
            {
                "email": "badadmin@test.com",
                "password": "testpassword123",
                "role": "admin",
            }
        ),
        content_type="application/json",
    )
    assert r.status_code == 403


def test_logout_blacklists_token(client):
    _, _, tok = register_and_login(client)
    lg = client.post(
        "/api/auth/logout", headers={"Authorization": f"Bearer {tok}"}
    )
    assert lg.status_code == 200
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
