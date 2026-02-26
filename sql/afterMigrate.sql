-- Ensure app_user has access to schemas
GRANT USAGE ON SCHEMA public TO ${app_user};
GRANT USAGE ON SCHEMA supplemented TO ${app_user};

-- Grant select on all existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ${app_user};
GRANT SELECT ON ALL TABLES IN SCHEMA supplemented TO ${app_user};

-- Ensure future tables are also covered (redundant with V1 but safe to keep here)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ${app_user};
ALTER DEFAULT PRIVILEGES IN SCHEMA supplemented GRANT SELECT ON TABLES TO ${app_user};
