#!/bin/bash
# Exit immediately if a command exits with a non-zero status.
set -e

# This script runs psql, passing in the SQL commands.
# It uses the environment variables that docker-compose provides.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    CREATE USER '$APP_DB_USER' WITH PASSWORD '$APP_DB_PASSWORD';

    GRANT CONNECT ON DATABASE $POSTGRES_DB TO gtfs_app;

    GRANT USAGE ON SCHEMA public TO gtfs_app;

    ALTER DEFAULT PRIVILEGES FOR USER $POSTGRES_USER IN SCHEMA public
    GRANT SELECT ON TABLES TO gtfs_app;

EOSQL
