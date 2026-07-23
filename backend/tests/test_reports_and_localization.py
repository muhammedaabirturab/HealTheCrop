def test_soil_health_report_flags_low_nitrogen(client, auth_token):
    resp = client.post(
        "/api/v1/reports/soil-health",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"nitrogen": 20, "phosphorus": 20, "potassium": 20, "ph": 5.0, "moisture": 20},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["fertility_score"] < 75
    assert len(body["suggestions"]) > 0


def test_soil_health_report_good_soil_no_suggestions(client, auth_token):
    resp = client.post(
        "/api/v1/reports/soil-health",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"nitrogen": 80, "phosphorus": 60, "potassium": 90, "ph": 6.8, "moisture": 50},
    )
    assert resp.status_code == 200
    assert resp.json()["fertility_score"] >= 75


def test_soil_health_report_rejects_wrong_types(client, auth_token):
    resp = client.post(
        "/api/v1/reports/soil-health",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"nitrogen": "not-a-number", "phosphorus": 20, "potassium": 20, "ph": 5.0, "moisture": 20},
    )
    assert resp.status_code == 422


def test_soil_health_report_rejects_out_of_range(client, auth_token):
    resp = client.post(
        "/api/v1/reports/soil-health",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"nitrogen": 20, "phosphorus": 20, "potassium": 20, "ph": 25, "moisture": 20},
    )
    assert resp.status_code == 422


def test_supported_languages_list(client):
    resp = client.get("/api/v1/localization/languages")
    assert resp.status_code == 200
    codes = [lang["code"] for lang in resp.json()]
    assert set(codes) == {"en", "hi", "kn", "ta", "te", "ml"}


def test_get_translation_bundle(client):
    resp = client.get("/api/v1/localization/hi")
    assert resp.status_code == 200
    assert resp.json()["app"]["name"]


def test_unsupported_language_404(client):
    resp = client.get("/api/v1/localization/fr")
    assert resp.status_code == 404
