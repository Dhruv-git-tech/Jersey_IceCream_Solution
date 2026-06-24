-- =============================================================================
-- Jersey Ice Cream Platform — PostgreSQL Initialization
-- =============================================================================
-- This script runs on first database container creation.
-- Creates required extensions and initial schema setup.
-- =============================================================================

-- Enable PostGIS for spatial queries (cart locations, territory boundaries)
CREATE EXTENSION IF NOT EXISTS postgis;

-- Enable pg_trgm for trigram-based fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable uuid-ossp for UUID generation (backup to application-side uuid4)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable btree_gist for exclusion constraints (territory non-overlap)
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Enable pgcrypto for additional cryptographic functions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Set timezone to UTC for consistency
ALTER DATABASE jersey_platform SET timezone TO 'UTC';

-- Create application schema (optional — using public for simplicity)
-- CREATE SCHEMA IF NOT EXISTS jersey;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Jersey Ice Cream Platform database initialized successfully';
    RAISE NOTICE 'Extensions: postgis, pg_trgm, uuid-ossp, btree_gist, pgcrypto';
END
$$;
