# Prometheus + Grafana monitoring stack

A self-contained observability setup: Prometheus scrapes a small demo service,
Grafana visualises it with a provisioned dashboard, and a set of alert rules
evaluates in the background.

Everything here is **configuration as code** — no clicking around in the UI to
create dashboards. Clone, run, and you get the same result every time.

---

## Architecture

```
                      scrape every 5s
   ┌────────────────┐  ────────────────►  ┌──────────────────┐
   │  checkout-api  │                     │   Prometheus     │
   │  (demo service)│  ◄────────────────  │   :9090          │
   │  :8080/metrics │      HTTP GET       │                  │
   └────────────────┘                     │  • TSDB          │
          ▲                               │  • alert rules   │
          │ real HTTP traffic             └────────┬─────────┘
          │                                        │ PromQL
   ┌────────────────┐                     ┌────────▼─────────┐
   │    loadgen     │                     │    Grafana       │
   │  ~18 req/s     │                     │    :3000         │
   └────────────────┘                     │  • provisioned   │
                                          │    datasource    │
                                          │  • provisioned   │
                                          │    dashboards    │
                                          └──────────────────┘
```

## Quick start

```powershell
# Windows — brings up all four processes and waits for readiness
powershell -ExecutionPolicy Bypass -File scripts\start.ps1

# then, once the charts have ~10 minutes of history:
powershell -ExecutionPolicy Bypass -File scripts\screenshot.ps1

# shut everything down
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
```

| Service | URL |
|---|---|
| Grafana dashboard | http://127.0.0.1:3000/d/service-overview |
| Prometheus targets | http://127.0.0.1:9090/targets |
| Prometheus alerts | http://127.0.0.1:9090/alerts |
| Demo service metrics | http://127.0.0.1:8080/metrics |

Grafana runs with anonymous admin access so screenshots work without a login
step. **This is a local demo only — never expose it as-is.**

---

## What's included

```
prometheus-grafana-demo/
├── demo-app/
│   ├── app.py                  demo HTTP service, exports Prometheus metrics
│   └── loadgen.py              generates realistic traffic against it
├── prometheus/
│   ├── prometheus.yml          scrape configs
│   └── alert-rules.yml         7 alert rules across availability/latency/saturation
├── provisioning/
│   ├── datasources/            Grafana datasource, provisioned
│   └── dashboards/             Grafana dashboard provider, provisioned
├── dashboards/
│   └── service-overview.json   the dashboard (13 panels)
├── scripts/
│   ├── start.ps1               bring the stack up
│   ├── stop.ps1                tear it down
│   ├── screenshot.ps1          capture the dashboard to PNG
│   └── build_dashboard.py      regenerate the dashboard JSON
└── gallery/                    screenshots
```

## The dashboard

Structured around the **RED method** (Rate, Errors, Duration) plus saturation
signals — the same layout used for real service dashboards.

| Row | Panels |
|---|---|
| Summary | Requests/sec, error rate, p95 latency, active DB connections, worker utilisation, cache hit ratio |
| Traffic | Request rate by endpoint (stacked), latency percentiles p50/p95/p99 |
| Health | Errors by response class, saturation (queue depth + worker utilisation) |
| Breakdown | Response status distribution, throughput by endpoint |

Panels use threshold colouring, so a degrading service turns yellow then red
without anyone having to read the numbers.

## Alert rules

| Alert | Condition | Severity |
|---|---|---|
| `ServiceDown` | `up == 0` for 30s | critical |
| `HighErrorRate` | 5xx ratio > 5% for 1m | critical |
| `ElevatedErrorRate` | 5xx ratio > 2% for 2m | warning |
| `HighLatencyP95` | p95 > 500ms for 1m | warning |
| `SlowEndpoint` | per-endpoint p95 > 2s for 1m | warning |
| `QueueBacklog` | queue depth > 30 for 2m | warning |
| `LowCacheHitRatio` | hit ratio < 90% for 2m | info |

Each rule carries a `summary`, a `description` and an `action` annotation, so
whoever is on call knows what to check first — not just that something is wrong.

---

## Design notes

**Configuration as code, not UI clicks.** The datasource and dashboard are
provisioned from files. That means they are reviewable in a pull request,
reproducible on a new host, and restorable after someone edits them by accident.

**The demo service measures itself.** `app.py` exports counters and a latency
histogram built from its own request handling. Nothing is hard-coded to look
good — the 5xx spike you see in the screenshots is a real error path being
exercised by real traffic.

**Leading indicators, not just symptoms.** Queue depth and worker utilisation
back up *before* latency visibly degrades. A dashboard that only shows CPU and
memory tells you about a problem after your users already found it.

**Latency as a histogram, not an average.** Averages hide the tail. p95 and p99
are what your slowest users actually experience, so the latency panels
calculate quantiles from histogram buckets.

## Adding another host

1. Install an exporter on the new host (`node_exporter` on Linux).
2. Add a target to the relevant `job_name` in `prometheus/prometheus.yml`.
3. Reload Prometheus: `curl -X POST http://127.0.0.1:9090/-/reload`.
4. The existing dashboard panels pick it up automatically — they aggregate by
   label rather than hard-coding instance names.

## Requirements

- Prometheus 3.x and Grafana 13.x (Windows binaries used here)
- Python 3.9+ (standard library only — no `pip install` needed)
- Chrome or Edge, for the screenshot script only

## Notes

- Prometheus data is retained for 7 days under `data/prometheus`.
- Alertmanager is intentionally omitted: firing alerts are visible in the
  Prometheus UI and in Grafana, which is enough for a demo. Wiring up
  Alertmanager is a small addition — add an `alerting.alertmanagers` entry to
  `prometheus.yml`.
