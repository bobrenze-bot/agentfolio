#!/bin/bash
# Database initialization script for PostgreSQL
# This script runs automatically when the postgres container starts

set -e

# Create extensions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable UUID extension
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Enable pg_trgm for trigram search (optional, for fuzzy matching)
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
    
    -- Enable btree_gin for composite indexes
    CREATE EXTENSION IF NOT EXISTS btree_gin;
EOSQL

echo "Database extensions created successfully"
