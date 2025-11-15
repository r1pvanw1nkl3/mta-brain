#!/bin/bash
# Exit immediately if a command exits with a non-zero status.
set -e

# This script runs psql, passing in the SQL commands.
# It uses the environment variables that docker-compose provides.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

    -- 1. Create the second, weaker user (gtfs_app)
    -- We can use the environment variable directly here because
    -- the shell script will expand it before psql runs.
    CREATE USER gtfs_app WITH PASSWORD '$APP_DB_PASSWORD';

    -- 2. Grant it permission to connect to the database
    GRANT CONNECT ON DATABASE $POSTGRES_DB TO gtfs_app;

    -- 3. Grant it read-only permissions on the public schema
    GRANT USAGE ON SCHEMA public TO gtfs_app;

    -- 4. Grant it SELECT (read) permissions on all tables
    -- that the ETL user ($POSTGRES_USER) creates in the future.
    ALTER DEFAULT PRIVILEGES FOR USER $POSTGRES_USER IN SCHEMA public
    GRANT SELECT ON TABLES TO gtfs_app;

EOSQL