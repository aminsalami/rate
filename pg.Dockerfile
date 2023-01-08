FROM  postgres:latest
COPY rates.sql /docker-entrypoint-initdb.d/01_rates.sql
COPY custom.sql /docker-entrypoint-initdb.d/09_custom.sql
