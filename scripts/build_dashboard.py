#!/usr/bin/env python3
"""
build_dashboard.py -- generates the provisioned Grafana dashboard JSON.

Writing 700 lines of dashboard JSON by hand is a good way to make a typo that
Grafana silently rejects, so the panels are built from templates here instead.

Run:  python build_dashboard.py
Out:  ../dashboards/service-overview.json
"""

import json
import os

DS = {"type": "prometheus", "uid": "prometheus-ds"}
UID = "service-overview"

RED = "red"
YELLOW = "yellow"
GREEN = "green"


def target(expr, legend=None, instant=False, ref="A"):
    t = {"refId": ref, "expr": expr, "datasource": DS}
    if legend:
        t["legendFormat"] = legend
    if instant:
        t["instant"] = True
        t["range"] = False
    return t


def base(panel_type, title, grid, targets, description=None):
    p = {
        "type": panel_type,
        "title": title,
        "datasource": DS,
        "gridPos": grid,
        "targets": targets,
        "fieldConfig": {"defaults": {}, "overrides": []},
        "options": {},
    }
    if description:
        p["description"] = description
    return p


def timeseries(title, grid, targets, unit="short", description=None, fill=14,
               legend_mode="list", legend_placement="bottom", stack=False,
               thresholds=None, max_val=None, min_val=None, decimals=2):
    p = base("timeseries", title, grid, targets, description)
    custom = {
        "drawStyle": "line",
        "lineInterpolation": "smooth",
        "lineWidth": 2,
        "fillOpacity": fill,
        "gradientMode": "opacity",
        "showPoints": "never",
        "spanNulls": False,
        "stacking": {"mode": "normal" if stack else "none", "group": "A"},
        "axisPlacement": "auto",
        "axisSoftMin": 0,
    }
    defaults = {
        "unit": unit,
        "decimals": decimals,
        "custom": custom,
        "color": {"mode": "palette-classic"},
    }
    if thresholds:
        defaults["thresholds"] = {"mode": "absolute", "steps": thresholds}
    if max_val is not None:
        defaults["max"] = max_val
    if min_val is not None:
        defaults["min"] = min_val
    p["fieldConfig"]["defaults"] = defaults
    p["options"] = {
        "legend": {
            "displayMode": legend_mode,
            "placement": legend_placement,
            "showLegend": True,
            "calcs": [],
        },
        "tooltip": {"mode": "multi", "sort": "desc"},
    }
    return p


def stat(title, grid, targets, unit="short", decimals=2, description=None,
         color_mode="value", graph_mode="area", thresholds=None, text_mode="value"):
    p = base("stat", title, grid, targets, description)
    defaults = {
        "unit": unit,
        "decimals": decimals,
        "color": {"mode": "thresholds"} if thresholds else {"mode": "palette-classic"},
    }
    if thresholds:
        defaults["thresholds"] = {"mode": "absolute", "steps": thresholds}
    p["fieldConfig"]["defaults"] = defaults
    p["options"] = {
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
        "colorMode": color_mode,
        "graphMode": graph_mode,
        "textMode": text_mode,
        "justifyMode": "auto",
        "orientation": "auto",
    }
    return p


def gauge(title, grid, targets, unit="percentunit", description=None, thresholds=None):
    p = base("gauge", title, grid, targets, description)
    p["fieldConfig"]["defaults"] = {
        "unit": unit,
        "min": 0,
        "max": 1,
        "decimals": 1,
        "color": {"mode": "thresholds"},
        "thresholds": {
            "mode": "absolute",
            "steps": thresholds or [
                {"color": RED, "value": None},
                {"color": YELLOW, "value": 0.9},
                {"color": GREEN, "value": 0.95},
            ],
        },
    }
    p["options"] = {
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
        "showThresholdLabels": False,
        "showThresholdMarkers": True,
    }
    return p


def piechart(title, grid, targets, description=None):
    p = base("piechart", title, grid, targets, description)
    p["fieldConfig"]["defaults"] = {
        "unit": "short",
        "decimals": 0,
        "color": {"mode": "palette-classic"},
    }
    p["options"] = {
        "reduceOptions": {"calcs": ["sum"], "fields": "", "values": False},
        "pieType": "donut",
        "tooltip": {"mode": "single", "sort": "none"},
        "legend": {
            "displayMode": "table",
            "placement": "right",
            "showLegend": True,
            "values": ["value", "percent"],
        },
    }
    return p


def bargauge(title, grid, targets, unit="reqps", description=None):
    p = base("bargauge", title, grid, targets, description)
    p["fieldConfig"]["defaults"] = {
        "unit": unit,
        "decimals": 2,
        "color": {"mode": "continuous-GrYlRd"},
        "min": 0,
    }
    p["options"] = {
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
        "displayMode": "gradient",
        "orientation": "horizontal",
        "showUnfilled": True,
    }
    return p


def text_panel(title, grid, markdown):
    return {
        "type": "text",
        "title": title,
        "gridPos": grid,
        "options": {"mode": "markdown", "content": markdown, "code": {"language": "plaintext", "showLineNumbers": False, "showMiniMap": False}},
        "transparent": True,
        "targets": [],
    }


# --------------------------------------------------------------------------
# Expressions
# --------------------------------------------------------------------------

RATE = 'sum(rate(demo_http_requests_total[1m]))'
ERR_RATE = ('100 * sum(rate(demo_http_requests_total{status=~"5.."}[1m]))'
            ' / clamp_min(sum(rate(demo_http_requests_total[1m])), 0.0001)')
P95 = ('histogram_quantile(0.95, sum(rate(demo_http_request_duration_seconds_bucket[1m])) by (le))')
P99 = ('histogram_quantile(0.99, sum(rate(demo_http_request_duration_seconds_bucket[1m])) by (le))')
P50 = ('histogram_quantile(0.50, sum(rate(demo_http_request_duration_seconds_bucket[1m])) by (le))')

panels = []

# --- header ---------------------------------------------------------------
panels.append(text_panel(
    "",
    {"h": 2, "w": 24, "x": 0, "y": 0},
    "**checkout-api** &nbsp;·&nbsp; service overview &nbsp;·&nbsp; RED method "
    "(rate, errors, duration) + saturation signals &nbsp;·&nbsp; "
    "scraped every 5s by Prometheus, `env=demo`",
))

# --- row 1: stats ---------------------------------------------------------
panels.append(stat(
    "Requests / sec", {"h": 4, "w": 4, "x": 0, "y": 2},
    [target(RATE, legend="req/s")],
    unit="reqps", decimals=1,
    description="Total request rate across all endpoints, 1 minute window.",
))
panels.append(stat(
    "Error rate", {"h": 4, "w": 4, "x": 4, "y": 2},
    [target(ERR_RATE, legend="5xx")],
    unit="percent", decimals=2,
    thresholds=[{"color": GREEN, "value": None},
                {"color": YELLOW, "value": 2},
                {"color": RED, "value": 5}],
    description="Share of 5xx responses. Alerting fires at 2% (warning) and 5% (critical).",
))
panels.append(stat(
    "p95 latency", {"h": 4, "w": 4, "x": 8, "y": 2},
    [target(P95, legend="p95")],
    unit="s", decimals=3,
    thresholds=[{"color": GREEN, "value": None},
                {"color": YELLOW, "value": 0.5},
                {"color": RED, "value": 1}],
))
panels.append(stat(
    "Active DB connections", {"h": 4, "w": 4, "x": 12, "y": 2},
    [target("demo_db_connections_active", legend="connections")],
    unit="short", decimals=1,
))
panels.append(gauge(
    "Worker utilisation", {"h": 4, "w": 4, "x": 16, "y": 2},
    [target("demo_worker_utilization", legend="utilisation")],
    thresholds=[{"color": GREEN, "value": None},
                {"color": YELLOW, "value": 0.7},
                {"color": RED, "value": 0.9}],
))
panels.append(gauge(
    "Cache hit ratio", {"h": 4, "w": 4, "x": 20, "y": 2},
    [target("demo_cache_hit_ratio", legend="hit ratio")],
    thresholds=[{"color": RED, "value": None},
                {"color": YELLOW, "value": 0.9},
                {"color": GREEN, "value": 0.95}],
))

# --- row 2 ----------------------------------------------------------------
panels.append(timeseries(
    "Request rate by endpoint", {"h": 8, "w": 12, "x": 0, "y": 6},
    [target('sum by (endpoint) (rate(demo_http_requests_total[1m]))', legend="{{endpoint}}")],
    unit="reqps", stack=True,
    description="Where the traffic actually goes. Stacked so the total is readable.",
))
panels.append(timeseries(
    "Latency percentiles", {"h": 8, "w": 12, "x": 12, "y": 6},
    [target(P50, legend="p50", ref="A"),
     target(P95, legend="p95", ref="B"),
     target(P99, legend="p99", ref="C")],
    unit="s", decimals=3, fill=8,
    thresholds=[{"color": GREEN, "value": None},
                {"color": YELLOW, "value": 0.5},
                {"color": RED, "value": 1}],
    description="p50/p95/p99 over a 1 minute window.",
))

# --- row 3 ----------------------------------------------------------------
panels.append(timeseries(
    "Errors by response class", {"h": 8, "w": 12, "x": 0, "y": 14},
    [target('sum by (status) (rate(demo_http_requests_total{status=~"[45].."}[1m]))',
            legend="HTTP {{status}}")],
    unit="reqps", stack=True, fill=25,
    description="4xx and 5xx response rates, split by status code.",
))
panels.append(timeseries(
    "Saturation: queue depth & worker utilisation", {"h": 8, "w": 12, "x": 12, "y": 14},
    [target("demo_queue_depth", legend="queue depth", ref="A"),
     target("100 * demo_worker_utilization", legend="worker utilisation %", ref="B")],
    unit="short", decimals=1,
    description="Leading indicators: the queue backs up before latency visibly degrades.",
))

# --- row 4 ----------------------------------------------------------------
panels.append(piechart(
    "Response status distribution", {"h": 8, "w": 10, "x": 0, "y": 22},
    [target('sum by (status) (increase(demo_http_requests_total[30m]))',
            legend="{{status}}", instant=True)],
    description="Cumulative response mix over the selected 30 minute window.",
))
panels.append(bargauge(
    "Throughput by endpoint", {"h": 8, "w": 14, "x": 10, "y": 22},
    [target('sum by (endpoint) (rate(demo_http_requests_total[5m]))',
            legend="{{endpoint}}", instant=True)],
    description="Current request rate per endpoint.",
))

dashboard = {
    "uid": UID,
    "title": "checkout-api — Service Overview",
    "description": "Request rate, errors and duration (RED) plus saturation signals for checkout-api.",
    "tags": ["demo", "prometheus", "grafana", "sre"],
    "timezone": "browser",
    "schemaVersion": 39,
    "version": 1,
    "editable": True,
    "graphTooltip": 1,
    "refresh": "5s",
    "time": {"from": "now-30m", "to": "now"},
    "timepicker": {},
    "templating": {"list": []},
    "annotations": {"list": []},
    "panels": panels,
}

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dashboards")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.normpath(os.path.join(out_dir, "service-overview.json"))
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(dashboard, fh, indent=2, ensure_ascii=False)

print(f"wrote {out_path}")
print(f"panels: {len(panels)}")
