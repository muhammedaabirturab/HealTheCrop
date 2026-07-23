def test_manual_prediction_returns_valid_crop(client, auth_token):
    resp = client.post(
        "/api/v1/predictions/manual",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "nitrogen": 90, "phosphorus": 45, "potassium": 40, "temperature": 25,
            "humidity": 82, "ph": 6.2, "rainfall": 230, "season": "Kharif", "location": "Karnataka",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["recommended_crop"]
    assert 0 <= body["confidence"] <= 1
    assert len(body["alternatives"]) == 5
    assert "crop_details" in body


def test_manual_prediction_requires_auth(client):
    resp = client.post("/api/v1/predictions/manual", json={
        "nitrogen": 90, "phosphorus": 45, "potassium": 40, "temperature": 25,
        "humidity": 82, "ph": 6.2, "rainfall": 230,
    })
    assert resp.status_code == 401


def test_manual_prediction_validates_ranges(client, auth_token):
    resp = client.post(
        "/api/v1/predictions/manual",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "nitrogen": -10, "phosphorus": 45, "potassium": 40, "temperature": 25,
            "humidity": 82, "ph": 6.2, "rainfall": 230,
        },
    )
    assert resp.status_code == 422


def test_prediction_history(client, auth_token):
    client.post(
        "/api/v1/predictions/manual",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "nitrogen": 90, "phosphorus": 45, "potassium": 40, "temperature": 25,
            "humidity": 82, "ph": 6.2, "rainfall": 230,
        },
    )
    resp = client.get("/api/v1/predictions/history", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
