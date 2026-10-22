# Database

PostgreSQL 16 is the system of record. Two roles are used:

| Role | Purpose | Privileges |
|---|---|---|
| `matchlens_owner` | Runs Alembic migrations only | Owns the schema |
| `matchlens_app` | Used by the running API | SELECT/INSERT/UPDATE/DELETE on tables; no DDL |

`init/01-roles.sql` creates both (run once as a superuser). Schema comes from Alembic (`backend/alembic`), not from SQL files.
See `docs/setup-windows.md` for exact commands and `docs/database-design.md` for the model.
