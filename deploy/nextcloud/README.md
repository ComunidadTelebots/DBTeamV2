Nextcloud (official) — Docker Compose

This directory contains a minimal Docker Compose setup to run the official Nextcloud image with a MariaDB backend for local testing.

Files:
- `docker-compose.yml` — Nextcloud + MariaDB, exposes Nextcloud on host port `8085`.

Quick start (requires Docker and Docker Compose):

1. From the repository root, run:

```powershell
cd deploy\nextcloud
docker compose up -d
```

2. Open http://localhost:8085 and follow the web installer. Use the following DB settings when prompted:
- Database user: `nextcloud`
- Database password: `nextcloud`
- Database name: `nextcloud`
- Database host: `db`

Notes:
- Change `MYSQL_ROOT_PASSWORD` and `MYSQL_PASSWORD` in `docker-compose.yml` for production.
- Volumes `nc-db` and `nc-data` persist DB and Nextcloud data.
- If port `8085` conflicts, edit `docker-compose.yml` `ports` mapping.
