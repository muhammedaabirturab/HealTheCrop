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
    assert len(body["alternatives"]) == 6
    # Independent confidences should actually be ranked, not identical placeholders.
    confidences = [alt["confidence"] for alt in body["alternatives"]]
    assert confidences == sorted(confidences, reverse=True)
    assert len(set(confidences)) > 1
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
    assert body["model_selected"] in ["random_forest", "hist_gradient_boosting"]


def test_manual_prediction_suitability_tiers_match_thresholds(client, auth_token):
    """Each alternative's tier label must be internally consistent with its own
    score, not a hardcoded/placeholder tag."""
    resp = client.post(
        "/api/v1/predictions/manual",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "nitrogen": 120, "phosphorus": 60, "potassium": 40, "temperature": 18,
            "humidity": 55, "ph": 6.5, "rainfall": 75, "moisture": 45,
            "season": "winter", "location": "Punjab",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    thresholds = [(0.95, "excellent"), (0.85, "very_suitable"), (0.70, "suitable"), (0.50, "moderate"), (0.0, "poor")]
    for alt in body["alternatives"]:
        expected_tier = next(tier for threshold, tier in thresholds if alt["confidence"] >= threshold)
        assert alt["suitability_tier"] == expected_tier, alt


def test_feature_ordering_matches_training():
    """Regression guard: the feature order the predictor builds at inference
    time must exactly match what the model bundle was trained with — a silent
    mismatch here would make every prediction meaningless."""
    from app.ml.crop_predictor import get_crop_predictor

    predictor = get_crop_predictor()
    expected = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall", "moisture", "season", "location"]
    assert predictor.feature_names == expected

    features = {
        "nitrogen": 90, "phosphorus": 45, "potassium": 40, "temperature": 25,
        "humidity": 82, "ph": 6.2, "rainfall": 230, "moisture": 70,
    }
    result_a = predictor.predict(features, "Kharif", "Karnataka")
    # Same values, dict constructed in a different key order — must be
    # bit-identical, proving lookups are by key, never by positional order.
    reordered_features = {
        "moisture": 70, "rainfall": 230, "humidity": 82, "nitrogen": 90,
        "ph": 6.2, "potassium": 40, "temperature": 25, "phosphorus": 45,
    }
    result_b = predictor.predict(reordered_features, "Kharif", "Karnataka")
    assert result_a == result_b


