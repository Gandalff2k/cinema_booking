# CinemaX

A backend for a cinema chain: customers browse movies, pick seats on a live seat map, pay through Stripe, and get their tickets by email with a QR code attached. Managers run everything — movies, reviews, refunds — from a dedicated admin dashboard.

The frontend is plain server-served HTML/CSS/JS (no build step, no framework) talking to a JSON API. Nginx serves the static pages and proxies both the API and the object storage behind one domain.

## Stack

- **FastAPI** — async JSON API, OpenAPI docs at `/docs` outside production.
- **PostgreSQL 14** via SQLAlchemy 2.0 (asyncpg) — reader/writer engine split, with writes and `SELECT ... FOR UPDATE` always routed to the writer.
- **Alembic** — migrations; CI applies them to a real Postgres to catch drift unit tests can't see.
- **Redis** — page caching, the rate limiter, and the Celery broker/result backend.
- **Celery** (worker + beat) — ticket generation/email, rating and popularity recalculation, and a periodic job that releases seats held by abandoned unpaid orders.
- **Stripe** — checkout + webhooks for payment; refunds triggered from the admin dashboard.
- **MinIO** — S3-compatible storage for movie posters, uploaded through the admin dashboard.
- **JWT + Passlib (bcrypt)** — stateless access tokens, hashed passwords.
- **Infra**: Docker Compose, Nginx, GitHub Actions (CI + SSH deploy).

## Architecture

Three layers: `api/` (routers, HTTP concerns only), `app/` (controllers, repositories, models, integrations — the actual business logic and data access), and `core/` (config, security, caching, database session management, cross-cutting FastAPI dependencies/middleware).

### Reader/writer session routing

`core/database/session.py` routes every query through one of two engines based on what it is: writes and locking reads (`SELECT ... FOR UPDATE`) go to the writer, everything else to the reader. This is transparent to the rest of the app — repositories just use `session` and the routing happens underneath.

### Idempotent payments

The Stripe webhook can be delivered more than once for the same event — Stripe does this on purpose. The order's own status is the idempotency guard: the row is locked, and if it's already `PAID` the handler returns immediately without touching anything else. A unique constraint on the payment's provider ID is the second line of defense for a concurrent duplicate that slips past the status check; that path is caught as an `IntegrityError` and treated as a no-op. Side effects (sending tickets, recalculating popular movies) fire exactly once, only on the real `PENDING → PAID` transition.

### Cache is fail-open, seats are not

Redis backs the read-through cache on the movie catalog and the rate limiter — both fine to lose. Seat holds are the opposite: locking a seat takes a real `SELECT ... FOR UPDATE` in Postgres inside the booking transaction, because a race there means double-selling a seat. A Celery beat job separately releases seats held by orders that went `PENDING` and were never paid within `STALE_ORDER_MINUTES`.

### Object storage stays behind the app, not in front of it

Admins upload posters through the app's own `/admin/movies/{id}/poster` endpoint, which validates the file and pushes it into MinIO — nobody needs direct MinIO access for day-to-day work. In production MinIO has no port published to the internet at all; only Nginx and the API can reach it, over the internal Docker network. 

## Running locally

```
docker compose up --build
```

Brings up Postgres, Redis, MinIO, the API (migrations run automatically on start), the Celery worker, and Nginx. Copy `.env.example` to `.env` first and fill in the values — at minimum `SECRET_KEY` (generate one, see the comment in the example file) and, if you want to test payments, a Stripe test-mode key.

Seed sample data (movies, halls, shows, an admin account, fake reviews):

```
docker compose exec api python -m app.seed
```

Run the test suite (unit tests need nothing running; integration tests need Postgres + Redis, which `docker compose up` already gives you):

```
poetry install
poetry run pytest
```

## Deployment

**CI** (`.github/workflows/ci.yml`) runs on pushes to `develop` and PRs into `main`/`develop`: Ruff (lint + format check), the full test suite against real Postgres + Redis service containers, and a dedicated job that applies every migration to a fresh Postgres to catch schema drift the SQLite-free test suite structurally can't.

**CD** (`.github/workflows/deploy.yml`) runs on push to `main`: re-runs the tests, then SSHes into the VM and runs `docker compose -f docker-compose.prod.yml up -d --build`. TLS certs live on the VM host (issued by certbot) and are bind-mounted read-only into Nginx — `nginx.prod.conf` only ever references a path, never a certificate.

### First-time VM setup

1. Point the domain's DNS at the VM.
2. Clone the repo, copy `.env.example` to `.env` and fill in production values (`ENVIRONMENT=production`, `DEBUG=0`, a real `SECRET_KEY`, live Stripe keys, `FRONTEND_URL=https://your-domain`, a strong `MINIO_ROOT_PASSWORD`, matching `POSTGRES_PASSWORD` in both `.env` and the URL inside `DATABASE_URL`).
3. Replace every `YOUR_DOMAIN` placeholder in `nginx.prod.conf` with the real domain.
4. Issue the first certificate. Nginx needs to be serving port 80 for the HTTP-01 challenge, so bring the stack up once before certs exist — the port-80 server block works without them:
   ```
   docker compose -f docker-compose.prod.yml up -d nginx
   sudo certbot certonly --webroot -w ./certbot-webroot -d YOUR_DOMAIN
   docker compose -f docker-compose.prod.yml up -d --build
   ```
5. Add a renewal cron/systemd timer on the host: `certbot renew --quiet --deploy-hook "docker compose -f /path/to/docker-compose.prod.yml exec nginx nginx -s reload"`.
6. Seed the database once: `docker compose -f docker-compose.prod.yml exec api python -m app.seed` (or apply your own initial data instead of the demo seed).

### Object storage in production

MinIO's ports are not published to the host in `docker-compose.prod.yml` — only containers on the compose network (Nginx, the API) can reach it. Two things stay true anyway:

- **Posters are still publicly viewable.** The app sets a public-*read* bucket policy on upload (`app/integrations/minio_client.py`), and Nginx proxies `/media/` to MinIO. Anyone can view a poster; nobody outside the network can list, write, or delete without the root credentials.
- **Admins still have convenient access when they need it**, without ever exposing MinIO to the internet:
  - The normal path is the admin dashboard's poster upload button — it goes through the API, not MinIO directly.
  - For anything else (bulk import, browsing the bucket), tunnel the console over SSH rather than opening a port: `ssh -L 9001:localhost:9001 user@vm-host`, then open `http://localhost:9001` locally and log in with `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`.
  - Or skip the console entirely: `docker compose -f docker-compose.prod.yml exec minio sh` and use the `mc` client already inside the image.


## Tests

- `tests/` — unit tests: JWT, password hashing, request-schema validation, exception codes, the cache key-maker, the ticket email builder. No services required.
- `tests/integration/` — auth, movies, reviews, admin (including pagination and search) against a real Postgres + Redis, driven through the app via an ASGI test client with dependency-free fixtures for creating users/admins/movies.
