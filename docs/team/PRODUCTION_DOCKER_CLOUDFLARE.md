# Production Docker and Public Routing Deployment

## Recommended Hostnames

Use one public app hostname for browser traffic and Stripe webhooks:

- Frontend: `https://transmuter.ishirock.tech`

The frontend nginx container serves the Angular app and proxies `/api` to the API
container over the Docker Compose network. A separate API hostname is optional
for direct API debugging, but it is not required for normal app or Stripe traffic.

## Local Production-Image Test

Run production-style containers locally:

```bash
./start-prod.sh
```

Local ports:

- Frontend: `http://localhost:4301`
- Backend: `http://localhost:8001`

Stop them:

```bash
./stop-prod.sh
```

## Runtime API URL

The web image is runtime-configurable. Set:

```bash
TRANSMUTER_API_URL=/api
```

The default is `/api`. The frontend nginx container proxies that same-origin path
to the API service over the Docker Compose network:

```bash
http://api:8001
```

## Public Routing

Current Hostinger/Traefik route:

| Public hostname | VPS loopback service |
| --- | --- |
| `transmuter.ishirock.tech` | `http://localhost:4301` |

Hostinger deployments are now run remotely through
`infra/hostinger/deploy-prod.sh` or
`CONFIRM_PROMOTE=1 infra/hostinger/promote-dev-to-prod.sh`. The local
production-image commands above are for developer or VPS-loopback diagnostics,
not the normal public deployment path.

The app normally uses the same-origin `/api` proxy. A separate public API
hostname is optional for debugging but is not part of the current production
runbook.

## Stripe Webhook

Configure Stripe webhook endpoint:

```text
https://transmuter.ishirock.tech/api/billing/webhook
```

Events:

- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

## CORS

The backend must allow the production frontend origin:

```text
https://transmuter.ishirock.tech
```

Keep Stripe webhooks pointed at the same-origin `/api` proxy unless a separate
API hostname is deliberately enabled.
