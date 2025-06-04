-- Travel Recharge API - Database Initialization
-- This file will be executed when the PostgreSQL container starts

-- Create extension for UUID generation if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Note: The full schema and data should be obtained from the external database repository
-- https://github.com/FreddyB200/travel-recharge-database.git
-- 
-- The repository contains:
-- - Schema files in db/data/
-- - 18 data insertion files in db/data/
-- - Stored procedures in db/data/
-- - Roles and permissions
--
-- This init.sql file will be replaced by the actual files from the database repository
-- during the container initialization process.

-- Basic table creation (minimal example)
-- TODO: Replace with actual schema from database repository

SELECT 'Database initialized successfully for Travel Recharge API' AS message; 