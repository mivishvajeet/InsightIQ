-- ====================================================================
-- InsightIQ Database Initialization: Schemas, Security Roles & Permissions
-- ====================================================================

-- 1. Create three-layer architecture schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;

-- 2. Create dedicated read-only role for the AI Agent SQL Tool
DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'insightiq_readonly') THEN
        CREATE ROLE insightiq_readonly WITH LOGIN PASSWORD 'readonly_secret';
    END IF;
END
$$;

-- 3. Configure query security and resource limits for the read-only user
-- Restrict execution time to 10 seconds to prevent denial of service from rogue queries
ALTER ROLE insightiq_readonly SET statement_timeout = '10s';
ALTER ROLE insightiq_readonly SET default_transaction_read_only = on;

-- 4. Grant connection permissions
GRANT CONNECT ON DATABASE insightiq TO insightiq_readonly;

-- 5. Schema permissions: read-only role has USAGE only on analytics schema
GRANT USAGE ON SCHEMA analytics TO insightiq_readonly;
REVOKE ALL ON SCHEMA raw FROM insightiq_readonly;
REVOKE ALL ON SCHEMA staging FROM insightiq_readonly;

-- 6. Set default table privileges for read-only user on analytics schema
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO insightiq_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON SEQUENCES TO insightiq_readonly;

-- 7. Explicitly revoke any destructive privileges
REVOKE CREATE ON SCHEMA raw FROM insightiq_readonly;
REVOKE CREATE ON SCHEMA staging FROM insightiq_readonly;
REVOKE CREATE ON SCHEMA analytics FROM insightiq_readonly;
