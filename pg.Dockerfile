FROM  postgres:latest
COPY rates.sql /docker-entrypoint-initdb.d/
COPY custom.sql /docker-entrypoint-initdb.d/
