#!/usr/bin/env bash
set -euo pipefail

# POSTGRES_MULTIPLE_DATABASES is a comma-separated list, e.g. "airflow,iceberg_catalog".
# The default POSTGRES_DB from docker-compose is created automatically by the
# postgres image itself, so this script only needs to create the others.
if [ -n "${POSTGRES_MULTIPLE_DATABASES:-}" ]; then
  IFS=',' read -ra DBS <<< "$POSTGRES_MULTIPLE_DATABASES"
  for db in "${DBS[@]}"; do
    if [ "$db" = "$POSTGRES_DB" ]; then
      continue
    fi
    echo "Creating database '$db' if it does not already exist"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
      SELECT 'CREATE DATABASE "$db"'
      WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
EOSQL
  done
fi
