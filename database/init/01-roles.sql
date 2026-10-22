-- Run ONCE as a PostgreSQL superuser, connected to the *matchlens* database:
--   psql -U postgres -d matchlens -v app_password="'<choose-a-password>'" -v owner_password="'<choose-another>'" -f 01-roles.sql
-- The owner role runs Alembic migrations. The app role can only read/write rows (no DDL).
CREATE ROLE matchlens_owner LOGIN PASSWORD :owner_password;
CREATE ROLE matchlens_app   LOGIN PASSWORD :app_password NOSUPERUSER NOCREATEDB NOCREATEROLE;
GRANT CONNECT ON DATABASE matchlens TO matchlens_owner, matchlens_app;
ALTER SCHEMA public OWNER TO matchlens_owner;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO matchlens_app;
GRANT ALL ON SCHEMA public TO matchlens_owner;
ALTER DEFAULT PRIVILEGES FOR ROLE matchlens_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO matchlens_app;
