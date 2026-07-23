import io

import cv2
import numpy as np


def _make_test_leaf_bytes() -> bytes:
    img = np.full((200, 200, 3), (40, 140, 40), dtype=np.uint8)
    cv2.circle(img, (100, 100), 25, (30, 90, 150), -1)
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
