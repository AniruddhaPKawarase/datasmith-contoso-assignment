-- Contoso read-only role — DB-level enforcement of the assignment's
-- "read-only DB credentials only" constraint (§4.4). App-layer sqlglot
-- guard is belt-and-suspenders.
--
-- Run against the contoso database as a superuser:
--   docker exec -i scm-postgres psql -U odoo -d contoso < scripts/setup_readonly_role.sql

-- 1. Role — safe to re-run (drops any prior definition)
DROP ROLE IF EXISTS contoso_reader;
CREATE ROLE contoso_reader LOGIN PASSWORD 'contoso_read_only';

-- 2. Grants: USAGE on schema, SELECT on all existing tables
GRANT USAGE ON SCHEMA public TO contoso_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO contoso_reader;

-- 3. Default privileges: any future table also gets SELECT-only
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO contoso_reader;

-- 4. Explicit revoke of everything else — no INSERT/UPDATE/DELETE/DDL
REVOKE ALL PRIVILEGES ON ALL TABLES    IN SCHEMA public FROM contoso_reader;
GRANT  SELECT                          ON ALL TABLES    IN SCHEMA public TO   contoso_reader;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM contoso_reader;
REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM contoso_reader;

-- 5. Verification: role should have only SELECT
--   psql: \du+ contoso_reader
--         SELECT has_table_privilege('contoso_reader','dimcustomer','SELECT'); -- t
--         SELECT has_table_privilege('contoso_reader','dimcustomer','INSERT'); -- f
