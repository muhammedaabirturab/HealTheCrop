import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)
settings = get_settings()


def seed_admin_account(db: Session) -> None:
    """Creates the default administrator account on first startup if no user
    with ADMIN_EMAIL exists yet. The password is hashed before storage — never
    stored or logged in plaintext. Idempotent: safe to call on every startup.

    No-op if ADMIN_EMAIL / ADMIN_PASSWORD aren't set via environment variables —
    there is no hardcoded fallback, so a fresh deployment simply has no admin
    account seeded until one is configured. Any admin account already in the
    database is untouched either way."""
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        logger.warning(
            "ADMIN_EMAIL / ADMIN_PASSWORD not set — skipping admin account seeding. "
            "Set both as environment variables to enable it."
        )
        return

    existing = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
    if existing:
        if existing.role != UserRole.ADMIN:
            existing.role = UserRole.ADMIN
            db.commit()
        return

    admin = User(
        name="Administrator",
        email=settings.ADMIN_EMAIL,
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        preferred_language="en",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    logger.info("Seeded default administrator account: %s", settings.ADMIN_EMAIL)
