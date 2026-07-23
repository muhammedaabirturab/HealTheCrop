def test_sensor_ingest_auto_registers_device(client):
    resp = client.post("/api/v1/sensors/ingest", json={
        "device_uid": "TEST-ESP32-01", "nitrogen": 50, "phosphorus": 30, "potassium": 35,
        "moisture": 45, "temperature": 27, "humidity": 60, "ph": 6.5, "rainfall": 100,
    })
    assert resp.status_code == 201
    assert resp.json()["device_id"] is not None


def test_device_list_requires_auth(client):
    resp = client.get("/api/v1/sensors/devices")
    assert resp.status_code == 401


def test_latest_reading_after_ingest(client, auth_token):
    client.post("/api/v1/sensors/ingest", json={
        "device_uid": "TEST-ESP32-02", "nitrogen": 50, "phosphorus": 30, "potassium": 35,
        "moisture": 45, "temperature": 27, "humidity": 60, "ph": 6.5, "rainfall": 100,
    })
    resp = client.get(
        "/api/v1/sensors/devices/TEST-ESP32-02/latest", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["nitrogen"] == 50


def test_latest_reading_unknown_device_404(client, auth_token):
    resp = client.get(
        "/api/v1/sensors/devices/DOES-NOT-EXIST/latest", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert resp.status_code == 404
