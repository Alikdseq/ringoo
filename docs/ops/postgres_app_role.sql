-- Ringoo PostgreSQL application role (least privilege).
-- Run as bootstrap/admin (ringoo_admin), NOT as the app role.
-- Do NOT run against production without a verified backup.
--
-- Replace passwords before use. Never commit real passwords.

-- CREATE ROLE ringoo_app WITH LOGIN PASSWORD 'REPLACE_APP_PASSWORD'
--   NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

-- GRANT CONNECT ON DATABASE ringoo TO ringoo_app;
-- \c ringoo
-- GRANT USAGE ON SCHEMA public TO ringoo_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ringoo_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ringoo_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public
--   GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ringoo_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public
--   GRANT USAGE, SELECT ON SEQUENCES TO ringoo_app;

-- Optional: revoke dangerous privileges if previously granted by mistake
-- REVOKE CREATE ON SCHEMA public FROM ringoo_app;
-- ALTER ROLE ringoo_app NOSUPERUSER NOCREATEDB NOCREATEROLE;

-- Application DATABASE_URL:
-- postgresql://ringoo_app:REPLACE_APP_PASSWORD@db:5432/ringoo
