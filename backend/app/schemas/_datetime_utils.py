from datetime import datetime, timezone


def as_utc(value: datetime | None) -> datetime | None:
    """Attach UTC tzinfo to a naive datetime before it's serialized to JSON.

    Every timestamp in this app is written with `datetime.now(timezone.utc)`,
    but SQLite has no native timezone-aware storage, so SQLAlchemy hands
    naive datetimes back on read even though the clock value is UTC. Without
    this, Pydantic serializes an ambiguous ISO string with no 'Z'/offset —
    and browsers parse that as the *viewer's local time*, not UTC, throwing
    every "time since" / freshness calculation off by the viewer's UTC
    offset (e.g. a reading that just arrived looks hours old, or from the
    future, depending on the sign).
    """
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)
