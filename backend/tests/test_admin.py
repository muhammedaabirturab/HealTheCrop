import pytest

from app.core.config import get_settings

settings = get_settings()


@pytest.fixture
def admin_token(client):
    resp = client.post("/api/v1/auth/login", json={
        "email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD,
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_admin_account_is_seeded_and_logs_in(client):
    resp = client.post("/api/v1/auth/login", json={
        "email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["role"] == "admin"
    assert body["user"]["email"] == settings.ADMIN_EMAIL


def test_register_cannot_self_assign_admin_role(client):
    """Regression test: RegisterRequest must never accept a `role` field —
    otherwise any client could self-promote to admin at signup."""
    resp = client.post("/api/v1/auth/register", json={
        "name": "Sneaky", "email": "sneaky@test.com", "password": "password123", "role": "admin",
    })
    assert resp.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": "sneaky@test.com", "password": "password123"})
    assert login.json()["user"]["role"] == "farmer"


def test_farmer_cannot_access_admin_endpoints(client, auth_token):
    resp = client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 403


def test_admin_can_view_stats_and_users(client, admin_token, auth_token):
    resp = client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["total_users"] >= 2  # admin + at least the pytest farmer

    resp = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert settings.ADMIN_EMAIL in emails
    assert "pytest@test.com" in emails


def test_admin_can_deactivate_and_reactivate_a_farmer(client, admin_token):
    client.post("/api/v1/auth/register", json={
        "name": "Deactivate Me", "email": "deactivateme@test.com", "password": "password123",
    })
    users = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"}).json()
    target = next(u for u in users if u["email"] == "deactivateme@test.com")

    resp = client.patch(
        f"/api/v1/admin/users/{target['id']}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    login = client.post("/api/v1/auth/login", json={"email": "deactivateme@test.com", "password": "password123"})
    assert login.status_code == 403

    resp = client.patch(
        f"/api/v1/admin/users/{target['id']}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": True},
    )
    assert resp.status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": "deactivateme@test.com", "password": "password123"})
    assert login.status_code == 200


def test_admin_cannot_deactivate_or_delete_admin_account(client, admin_token):
    users = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"}).json()
    admin_user = next(u for u in users if u["email"] == settings.ADMIN_EMAIL)

    resp = client.patch(
        f"/api/v1/admin/users/{admin_user['id']}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert resp.status_code == 400

    resp = client.delete(
        f"/api/v1/admin/users/{admin_user['id']}", headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


def test_admin_can_delete_a_farmer_account(client, admin_token):
    client.post("/api/v1/auth/register", json={
        "name": "Delete Me", "email": "deleteme@test.com", "password": "password123",
    })
    users = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"}).json()
    target = next(u for u in users if u["email"] == "deleteme@test.com")

    resp = client.delete(
        f"/api/v1/admin/users/{target['id']}", headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204

    login = client.post("/api/v1/auth/login", json={"email": "deleteme@test.com", "password": "password123"})
    assert login.status_code == 401


def test_admin_login_history_and_csv_export(client, admin_token, auth_token):
    resp = client.get("/api/v1/admin/login-history", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp = client.get("/api/v1/admin/export/users.csv", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "email" in resp.text.splitlines()[0]


def test_admin_can_view_predictions_and_pest_scans(client, admin_token, auth_token):
    client.post(
        "/api/v1/predictions/manual",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"nitrogen": 90, "phosphorus": 45, "potassium": 40, "temperature": 25,
              "humidity": 82, "ph": 6.2, "rainfall": 230},
    )
    resp = client.get("/api/v1/admin/predictions", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert resp.json()[0]["user_email"]

    resp = client.get("/api/v1/admin/pest-scans", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200


def test_remember_me_issues_refresh_token_and_refresh_endpoint_works(client):
    client.post("/api/v1/auth/register", json={
        "name": "Remember Me", "email": "rememberme@test.com", "password": "password123",
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "rememberme@test.com", "password": "password123", "remember_me": True,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["refresh_token"]

    refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert refresh_resp.status_code == 200
    assert refresh_resp.json()["access_token"]
    assert refresh_resp.json()["refresh_token"]


def test_login_without_remember_me_has_no_refresh_token(client):
    client.post("/api/v1/auth/register", json={
        "name": "No Remember", "email": "noremember@test.com", "password": "password123",
    })
    resp = client.post("/api/v1/auth/login", json={"email": "noremember@test.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["refresh_token"] is None


def test_refresh_rejects_an_access_token(client, auth_token):
    """An access token must not work as a refresh token."""
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": auth_token})
    assert resp.status_code == 401
