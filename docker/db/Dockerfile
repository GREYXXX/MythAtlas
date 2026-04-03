# pgvector is preinstalled; add PostGIS packages from the same PG 16 / Bookworm stack.
FROM pgvector/pgvector:pg16-bookworm

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-16-postgis-3 \
        postgresql-16-postgis-3-scripts \
    && rm -rf /var/lib/apt/lists/*

USER postgres
