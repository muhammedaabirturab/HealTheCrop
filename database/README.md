# Database

Alembic migrations live in [`../backend/alembic/`](../backend/alembic/) (they need to sit
next to `alembic.ini` and the SQLAlchemy models they introspect). This folder exists to
satisfy the documented project layout; see:

- [Database Schema](../docs/database_schema.md) — table-by-table reference
- [ER Diagram](../docs/er_diagram.md) — relationship diagram
- [`../backend/alembic/versions/`](../backend/alembic/versions/) — migration history
