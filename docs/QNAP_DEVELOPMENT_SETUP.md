# QNAP Development Setup

This guide targets QNAP TS-464 / QTS with Container Station.

## Files

- `docker-compose.qnap.yml`: QNAP development stack.
- `.env.qnap.example`: environment template.
- `docker/entrypoint.sh`: runs migrations, collectstatic, and optional test user creation.

## Prepare

Copy the repository to a QNAP shared folder, then create the local environment file:

```bash
cp .env.qnap.example .env.qnap
```

Edit `.env.qnap` before startup:

- Change `SECRET_KEY`.
- Change `DB_PASSWORD` and `POSTGRES_PASSWORD` to the same value.
- Change `DEV_LOGIN_PASSWORD`.
- If the NAS address changes, update `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `PUBLIC_SITE_URL`.

For the current NAS:

- Host: `NAS-CTHULHU`
- IP: `192.168.0.139`
- App URL: `http://NAS-CTHULHU:8000/`

## Start

From the repository directory on the NAS:

```bash
docker compose --env-file .env.qnap -f docker-compose.qnap.yml up -d --build
```

Check logs:

```bash
docker compose --env-file .env.qnap -f docker-compose.qnap.yml logs -f web
```

## Test Login

When `CREATE_DEV_LOGIN_USER=True`, startup creates or updates the user configured in `.env.qnap`.

Default template values:

- URL: `http://NAS-CTHULHU:8000/accounts/login/`
- Username/email field: `testuser`
- Password: value of `DEV_LOGIN_PASSWORD`

The development quick login page is also available while `DEBUG=True`:

```text
http://NAS-CTHULHU:8000/accounts/dev-login/
```

## Common Commands

Run migrations manually:

```bash
docker compose --env-file .env.qnap -f docker-compose.qnap.yml exec web python manage.py migrate --noinput
```

Create another development login user:

```bash
docker compose --env-file .env.qnap -f docker-compose.qnap.yml exec web \
  python manage.py ensure_dev_login_user \
  --username player1 \
  --password change-this-player-password \
  --email player1@example.local \
  --nickname Player1
```

Stop the stack:

```bash
docker compose --env-file .env.qnap -f docker-compose.qnap.yml down
```

Remove database/static/media volumes:

```bash
docker compose --env-file .env.qnap -f docker-compose.qnap.yml down -v
```
