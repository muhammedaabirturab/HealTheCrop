def test_register_and_login(client):
    resp = client.post("/api/v1/auth/register", json={
        "name": "Auth Test", "email": "auth1@test.com", "password": "password123",
    })
    assert resp.status_code == 201
    assert resp.json()["email"] == "auth1@test.com"

    resp = client.post("/api/v1/auth/login", json={"email": "auth1@test.com", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_duplicate_registration_rejected(client):
    client.post("/api/v1/auth/register", json={"name": "Dup", "email": "dup@test.com", "password": "password123"})
    resp = client.post("/api/v1/auth/register", json={"name": "Dup", "email": "dup@test.com", "password": "password123"})
    assert resp.status_code == 400


def test_login_wrong_password_rejected(client):
    client.post("/api/v1/auth/register", json={"name": "Wrong", "email": "wrong@test.com", "password": "password123"})
    resp = client.post("/api/v1/auth/login", json={"email": "wrong@test.com", "password": "badpassword"})
    assert resp.status_code == 401


def test_me_requires_token(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_with_valid_token(client, auth_token):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "pytest@test.com"
