import io

import cv2
import numpy as np


def _make_test_leaf_bytes() -> bytes:
    # Real photos always carry natural texture/noise; a perfectly flat synthetic
    # image would (correctly) get rejected by the blur-detection quality gate,
    # so we add noise to make this fixture representative of an actual photo.
    rng = np.random.default_rng(42)
    img = np.full((200, 200, 3), (40, 140, 40), dtype=np.uint8)
    cv2.circle(img, (100, 100), 25, (30, 90, 150), -1)
    noise = rng.normal(0, 12, img.shape)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    success, buf = cv2.imencode(".jpg", img)
    assert success
    return buf.tobytes()


def test_pest_scan_returns_detections(client, auth_token):
    image_bytes = _make_test_leaf_bytes()
    resp = client.post(
        "/api/v1/pest/scan",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("leaf.jpg", io.BytesIO(image_bytes), "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_used"] in ("heuristic", "cnn")
    assert len(body["detections"]) >= 1


def test_pest_scan_with_extensionless_filename_does_not_crash(client, auth_token):
    """Regression test: a filename with no '.' must not crash the storage-key builder
    (previously `"." in file.filename` combined with an unguarded .split() could raise
    on falsy filenames; this exercises the same branch with a real multipart upload)."""
    image_bytes = _make_test_leaf_bytes()
    resp = client.post(
        "/api/v1/pest/scan",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("leaf_photo", io.BytesIO(image_bytes), "image/jpeg")},
    )
    assert resp.status_code == 200


def test_pest_scan_rejects_bad_content_type(client, auth_token):
    resp = client.post(
        "/api/v1/pest/scan",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 400


def test_pest_scan_requires_auth(client):
    image_bytes = _make_test_leaf_bytes()
    resp = client.post(
        "/api/v1/pest/scan",
        files={"file": ("leaf.jpg", io.BytesIO(image_bytes), "image/jpeg")},
    )
    assert resp.status_code == 401


def test_pest_scan_rejects_blurry_image(client, auth_token):
    """A flat, textureless image (no natural photo noise) should be caught by
    the blur-detection quality gate instead of producing an unreliable guess."""
    img = np.full((200, 200, 3), (40, 140, 40), dtype=np.uint8)
    success, buf = cv2.imencode(".jpg", img)
    assert success
    resp = client.post(
        "/api/v1/pest/scan",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("blurry.jpg", io.BytesIO(buf.tobytes()), "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["image_quality"]["is_acceptable"] is False
    assert "blurry" in body["image_quality"]["issues"]
    assert body["detections"] == []
    assert body["is_uncertain"] is True


def test_pest_scan_rejects_non_plant_image(client, auth_token):
    """A photo with no plant-like colors at all (e.g. a plain gray wall) should
    be rejected rather than matched against random leaf-symptom candidates."""
    rng = np.random.default_rng(7)
    img = np.full((200, 200, 3), (120, 120, 120), dtype=np.uint8)
    noise = rng.normal(0, 8, img.shape)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    success, buf = cv2.imencode(".jpg", img)
    assert success
    resp = client.post(
        "/api/v1/pest/scan",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("wall.jpg", io.BytesIO(buf.tobytes()), "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["image_quality"]["is_acceptable"] is False
    assert "no_plant_detected" in body["image_quality"]["issues"]
