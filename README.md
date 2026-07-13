# NetOps Dashboard

A self-hosted, containerized network monitoring stack. A lightweight Python
agent pings a configurable list of hosts/devices, exposes latency and
uptime as Prometheus metrics, and Grafana visualizes them on a live
dashboard — with optional webhook alerts (Slack/Discord) when a host goes
down.

Built to give small teams/homelabs enterprise-style network observability
without any paid tooling.

## Architecture

```
 ┌────────────┐      /metrics       ┌────────────┐      query      ┌───────────┐
 │ NetOps     │ ------------------> │ Prometheus │ ---------------> │  Grafana  │
 │ Agent      │   (scraped every    │            │                  │ Dashboard │
 │ (pings     │    15s)             │            │                  │           │
 │  hosts)    │                     └────────────┘                  └───────────┘
 └────────────┘
       |
       v (on repeated failure)
   Webhook alert (Slack/Discord)

```

Three containers, wired together with Docker Compose:
- **agent** — Python service that pings hosts on an interval and exposes
  `netops_host_up` and `netops_host_latency_ms` metrics in Prometheus
  exposition format on `/metrics`.
- **prometheus** — scrapes the agent every 15s and stores the time series.
- **grafana** — auto-provisioned datasource + dashboard showing host
  up/down status and latency over time.

## Quick start

```bash
git clone <this-repo-url>
cd netops-dashboard
docker compose up -d --build
```

Then open:
- Grafana dashboard: http://localhost:3000 (anonymous viewer access enabled,
  or log in with `admin` / `admin`)
- Raw agent metrics: http://localhost:9105/metrics
- Prometheus UI: http://localhost:9090

## Configuration

Set these via environment variables in `docker-compose.yml` under the
`agent` service:

| Variable | Default | Description |
|---|---|---|
| `MONITOR_HOSTS` | `8.8.8.8,1.1.1.1` | Comma-separated hosts/IPs to monitor |
| `CHECK_INTERVAL_SECONDS` | `15` | How often to ping each host |
| `DOWN_THRESHOLD` | `3` | Consecutive failed pings before firing an alert |
| `ALERT_WEBHOOK_URL` | _(unset)_ | Slack/Discord-compatible webhook URL for alerts |

## Why this project

Built to demonstrate practical infrastructure/networking fundamentals:
container orchestration with Docker Compose, exposing custom metrics in a
format a real monitoring stack (Prometheus) understands, and turning raw
network data into an operational dashboard — the same pattern used in
production NOC/SRE tooling, just scoped down to something that runs on a
laptop or a $5 VM.

## Roadmap / possible extensions

- [ ] Add TCP port checks (not just ICMP ping) for monitoring specific services
- [ ] Persist historical uptime % per host for SLA-style reporting
- [ ] Add a simple traceroute panel for down hosts
- [ ] Package agent config as YAML instead of env vars for larger host lists

## License

MIT
