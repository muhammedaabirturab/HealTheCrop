import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_healthecrop.db"
# Config no longer ships hardcoded admin defaults (see app/core/config.py) —
# tests need their own admin credentials so seed_admin_account() has something
# to seed and test_admin.py has something to log in with.
os.environ.setdefault("ADMIN_EMAIL", "test-admin@healthecrop-test.com")
os.environ.setdefault("ADMIN_PASSWORD", "TestAdminPass123!")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from app.core.admin_seed import seed_admin_account
from app.core.database import Base, SessionLocal, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_admin_account(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    db_file = Path("test_healthecrop.db")
    if db_file.exists():
        db_file.unlink(missing_ok=True)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    client.post("/api/v1/auth/register", json={
        "name": "Pytest Farmer", "email": "pytest@test.com", "password": "password123", "location": "Karnataka",
    })
    resp = client.post("/api/v1/auth/login", json={"email": "pytest@test.com", "password": "password123"})
    return resp.json()["access_token"]
