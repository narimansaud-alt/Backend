# Production deployment on a Proxmox VM with Nginx Proxy Manager

The application VM runs the frontend and backend containers. Nginx Proxy Manager (NPM) runs in a separate LXC and is the only public entry point.

```text
Internet
   |
Nginx Proxy Manager LXC
   |-- app.example.com -> VM_IP:3000  (Next.js)
   `-- api.example.com -> VM_IP:8000  (FastAPI)
```

## 1. Prepare the VM

Install Docker Engine and the Compose plugin on the VM, then copy the repository to the VM. Create the shared network once:

```bash
docker network create app-network
cp .env.example .env
```

Set the production values in `.env`:

```dotenv
ENVIRONMENT=production
DOMAIN=app.example.com
FRONTEND_PUBLIC_API_URL=https://api.example.com
BACKEND_CORS_ORIGINS=https://app.example.com
POSTGRES_SERVER=db
POSTGRES_PORT=5432
REDIS_HOST=redis
STORAGE_HOST=minio
INITIAL_ADMIN_EMAIL=owner@example.com
INITIAL_ADMIN_USERNAME=owner
INITIAL_ADMIN_PASSWORD=replace-with-a-strong-unique-password
INITIAL_ORGANIZATION_NAME="Основная организация"
```

Also set all required secrets and infrastructure credentials from `.env.example`, especially `SECRET_KEY`, `JWT_SECRET_KEY`, `POSTGRES_*`, and `BROKER_URL`. The initial password must contain uppercase and lowercase letters, a digit, and a special character. The backend refuses to start in production with the example password.

Run migrations first, then start the application:

```bash
docker compose --profile migrations -f docker-compose.yaml -f docker-compose.proxmox.yml run --rm migrations
docker compose --profile api --profile storage --profile kafka -f docker-compose.yaml -f docker-compose.proxmox.yml up -d --build
```

On the first API startup the backend creates this verified `super_admin`, an organization, and an `owner` membership. Later restarts are idempotent and do not reset the password.

The VM must allow TCP 3000 and 8000 from the NPM LXC address. Do not forward these ports directly from the router to the VM; forward 80/443 to NPM only.

## 2. Configure DNS and NPM

Create `A`/`AAAA` records for both hostnames pointing to the public address of the NPM LXC:

- `app.example.com`
- `api.example.com`

In NPM create two Proxy Hosts:

| Domain | Forward hostname/IP | Forward port | Websockets |
|---|---:|---:|---|
| `app.example.com` | VM address | `3000` | On |
| `api.example.com` | VM address | `8000` | On |

Request a separate Let's Encrypt certificate for both names, enable **Force SSL** and **HTTP/2**. Keep the default proxy headers; NPM must forward `Host`, `X-Real-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto`.

## 3. Refresh-token cookie contract

Authentication is intentionally proxied by Next.js through same-origin routes:

1. Browser sends credentials to `https://app.example.com/api/auth/login`.
2. Next.js calls `http://app:8000/api/v1/auth/login` over the Docker network.
3. Next.js stores the rotated refresh token on the frontend host as:

```http
Set-Cookie: refresh_token=...; Path=/; HttpOnly; Secure; SameSite=Strict
```

4. When access expires, the browser calls `https://app.example.com/api/auth/refresh`; Next.js forwards the cookie to FastAPI and stores the rotated cookie again.

Do not change the cookie to `SameSite=None`, do not expose it to JavaScript, and do not set a `Domain` attribute. `NEXT_PUBLIC_API_URL` is the public API URL used for browser API requests; the refresh cookie itself stays on the frontend host.

## 4. Smoke checks

From the VM:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -I http://127.0.0.1:3000
```

From a client outside the VM:

```bash
curl -fsS https://api.example.com/health
curl -I https://app.example.com
```

After login, verify in browser DevTools that `refresh_token` is marked `HttpOnly`, `Secure`, `SameSite=Strict`, and `Path=/`, and that it is not readable through `document.cookie`.
