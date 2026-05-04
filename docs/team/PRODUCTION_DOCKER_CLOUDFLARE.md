# Production Docker and Cloudflare Deployment

## Recommended Hostnames

Use two hostnames:

- Frontend: `https://transmuter.ishirock.com`
- Backend API: `https://transmuter-api.ishirock.com`

This is the better launch setup for Transmuter because it gives the API an explicit origin for Stripe webhooks, operational logs, Cloudflare rules, rate limits, and future API-specific monitoring.

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
TRANSMUTER_API_URL=https://transmuter-api.ishirock.com
```

For local container testing, `start-prod.sh` defaults this to:

```bash
http://localhost:8001
```

## Cloudflare Tunnel Routing

Recommended tunnel routes:

| Public hostname | Local service |
| --- | --- |
| `transmuter.ishirock.com` | `http://localhost:4301` |
| `transmuter-api.ishirock.com` | `http://localhost:8001` |

## Stripe Webhook

Configure Stripe webhook endpoint:

```text
https://transmuter-api.ishirock.com/billing/webhook
```

Events:

- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

## CORS

The backend must allow the production frontend origin:

```text
https://transmuter.ishirock.com
```

Keep Stripe webhooks pointed at the API hostname, not the frontend hostname.
