#!/bin/sh
set -e
psql -v ON_ERROR_STOP=1 -U postgres -d matchlens \
  -v app_password="'${APP_DB_PASSWORD}'" -v owner_password="'${OWNER_DB_PASSWORD}'" \
  -f /sql/01-roles.sql
