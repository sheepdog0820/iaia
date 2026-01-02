# Required settings checklist (Local / Stg / Prod)

This file lists the values you still need to set by hand.

## Common (all environments)

- Create the env file from the example and fill in the required values.
  - Local: `.env.development`
  - Stg: `.env.staging`
  - Prod: `.env.production`
- Required keys in each env file:
  - `SECRET_KEY`
  - `ALLOWED_HOSTS`
  - `CSRF_TRUSTED_ORIGINS`
  - `SITE_ID`
  - `DB_ENGINE` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT`
- If using Django Sites, create separate Site records per environment.

## Local (Dev)

- `.env.development`
  - `ALLOWED_HOSTS=localhost,127.0.0.1`
  - `CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000`
  - `SITE_ID=1` (or your local Site ID)
  - DB values as needed (SQLite default if you keep dev DB local)
- Run with: `ENV_FILE=.env.development python manage.py runserver`

## Staging (stg.tableno.jp)

- `.env.staging`
  - `ALLOWED_HOSTS=stg.tableno.jp`
  - `CSRF_TRUSTED_ORIGINS=https://stg.tableno.jp`
  - `SITE_ID=2` (or your staging Site ID)
  - DB values (MySQL on compose or RDS endpoint)
- `nginx.conf` on the stg instance:
  - `server_name stg.tableno.jp;`

## Production (app.tableno.jp)

- `.env.production`
  - `ALLOWED_HOSTS=app.tableno.jp`
  - `CSRF_TRUSTED_ORIGINS=https://app.tableno.jp`
  - `SITE_ID=1` (or your production Site ID)
  - DB values (MySQL on compose or RDS endpoint)
- `nginx.conf` on the prod instance:
  - `server_name app.tableno.jp;`

## DNS (per environment)

- `app.tableno.jp` -> prod Lightsail static IP
- `stg.tableno.jp` -> stg Lightsail static IP

## SSL (per environment)

- Certificates are stored at:
  - `./ssl/fullchain.pem`
  - `./ssl/privkey.pem`
- Use: `ENV_FILE=.env.staging ./scripts/renew_certbot.sh` (or `.env.production`)

## Compose (per environment)

- Stg: `ENV_FILE=.env.staging docker compose -f docker-compose.mysql.yml up -d --build`
- Prod: `ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d --build`
