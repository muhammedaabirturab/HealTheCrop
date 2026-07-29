def test_manual_prediction_returns_valid_crop(client, auth_token):
    resp = client.post(
        "/api/v1/predictions/manual",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "nitrogen": 90, "phosphorus": 45, "potassium": 40, "temperature": 25,
            "humidity": 82, "ph": 6.2, "rainfall": 230, "season": "summer", "location": "Karnataka",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["recommended_crop"]
    assert 0 <= body["confidence"] <= 1
    assert len(body["alternatives"]) == 9
    assert "crop_details" in body
    assert body["season_used"] == "summer"
    assert body["explanation"]


def test_manual_prediction_maps_farmer_season_to_model_season(client, auth_token):
    """The farmer picks a calendar season (spring/summer/autumn/winter); the model
    should still receive Kharif/Rabi/Zaid under the hood, invisibly to the API caller."""
    for ui_season in ["spring", "summer", "autumn", "winter"]:
        resp = client.post(
            "/api/v1/predictions/manual",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "nitrogen": 90, "phosphorus": 45, "potassium": 40, "temperature": 25,
                "humidity": 82, "ph": 6.2, "rainfall": 230, "season": ui_season,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["season_used"] == ui_season


def test_manual_prediction_unrecognized_season_falls_back_to_auto_detect(client, auth_token):
    resp = client.post(
        "/api/v1/predictions/manual",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "nitrogen": 90, "phosphorus": 45, "potassium": 40, "temperature": 25,
            "humidity": 82, "ph": 6.2, "rainfall": 230, "season": "not-a-real-season",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["season_used"] in ["spring", "summer", "autumn", "winter"]


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


def test_model_info_reports_real_evaluation_metrics(client, auth_token):
    resp = client.get("/api/v1/predictions/model-info", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert 0 <= body["accuracy"] <= 1
    assert 0 <= body["cv_mean_accuracy"] <= 1
    assert body["n_classes"] >= 50
    assert len(body["classes"]) == body["n_classes"]


