
GRANT USAGE ON SCHEMA public TO ${app_user};
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ${app_user};

GRANT USAGE ON SCHEMA supplemented TO ${app_user};
GRANT SELECT ON ALL TABLES IN SCHEMA supplemented TO ${app_user};

ALTER DEFAULT PRIVILEGES IN SCHEMA supplemented GRANT SELECT ON TABLES TO ${app_user};
