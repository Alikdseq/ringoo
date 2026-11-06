-- Optional migration role (CREATE on schema). Runtime app uses ringoo_app instead.
-- Run as bootstrap/admin after backup. Do not use on production without review.

-- CREATE ROLE ringoo_migrate WITH LOGIN PASSWORD 'REPLACE_MIGRATE_PASSWORD'
--   NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

-- GRANT CONNECT ON DATABASE ringoo TO ringoo_migrate;
-- \c ringoo
-- GRANT USAGE, CREATE ON SCHEMA public TO ringoo_migrate;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ringoo_migrate;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ringoo_migrate;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ringoo_migrate;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ringoo_migrate;

-- After migrate, run app with DATABASE_URL for ringoo_app (DML only).
