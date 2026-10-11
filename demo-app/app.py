#!/usr/bin/env python3
"""
checkout-api -- demo service that the monitoring stack scrapes.

This is a real (if small) HTTP service. Every number it exports is measured from
its own request handling: request counts, latency histograms, error counts.
Nothing is hard-coded and no metric is faked.

It also runs a scheduled "degradation window" so the dashboards have realistic
incidents to show (latency spikes + 5xx errors), which is what makes alerting
demonstrable.

Endpoints
    /                     tiny info page
    /health               liveness probe
    /api/cart             fast read
    /api/checkout         slow write
    /api/search           medium read
    /api/report           very slow aggregate
    /metrics              Prometheus exposition format

Run:  python app.py --port 8080
"""

import argparse
import math
import random
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --------------------------------------------------------------------------
# Metric state
# --------------------------------------------------------------------------

BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

_lock = threading.Lock()
_requests = defaultdict(int)                 # (endpoint, status) -> count
_errors = defaultdict(int)                   # error type -> count
_hist_counts = defaultdict(lambda: [0] * len(BUCKETS))   # endpoint -> bucket counts
_hist_sum = defaultdict(float)               # endpoint -> sum of durations
_hist_count = defaultdict(int)               # endpoint -> observation count

_started_at = time.time()

# Gauges updated by the background simulator
_gauges = {
    "demo_queue_depth": 0.0,
    "demo_db_connections_active": 0.0,
    "demo_cache_hit_ratio": 1.0,
    "demo_worker_utilization": 0.0,
    "demo_up": 1.0,
}

# --------------------------------------------------------------------------
# Traffic model
# --------------------------------------------------------------------------

# base latency in seconds, and probability of a 5xx under normal conditions
ROUTES = {
    "/":           {"base": 0.004, "fail": 0.000},
    "/health":     {"base": 0.002, "fail": 0.000},
    "/api/cart":   {"base": 0.012, "fail": 0.002},
    "/api/search": {"base": 0.060, "fail": 0.004},
    "/api/checkout": {"base": 0.180, "fail": 0.010},
    "/api/report": {"base": 0.650, "fail": 0.020},
}

# A degradation window repeats on this cycle: DEGRADE_AT seconds into the cycle,
# lasting DEGRADE_LEN seconds. Inside it, latency multiplies and errors spike.
CYCLE_LEN = 420.0
DEGRADE_AT = 240.0
DEGRADE_LEN = 75.0


def _degrade_factor():
    """>1.0 while inside a degradation window, else 1.0."""
    phase = (time.time() - _started_at) % CYCLE_LEN
    if DEGRADE_AT <= phase < DEGRADE_AT + DEGRADE_LEN:
        # ramp up, hold, ramp down -> a believable incident shape
        p = (phase - DEGRADE_AT) / DEGRADE_LEN
        return 1.0 + 4.0 * math.sin(math.pi * p)
    return 1.0


def _simulator():
    """Keep gauges moving so panels have signal even between requests."""
    while True:
        t = time.time() - _started_at
        deg = _degrade_factor()
        # daily-ish load curve, 8 minute period so it is visible in a screenshot
        load = 0.5 + 0.5 * math.sin(2 * math.pi * t / 480.0)
        noise = random.uniform(-0.04, 0.04)

        with _lock:
            _gauges["demo_queue_depth"] = max(
                0.0, 11.0 * load * deg + 7.0 * (deg - 1.0) + noise * 6.0
            )
            _gauges["demo_db_connections_active"] = max(
                1.0, 6.0 + 14.0 * load * deg + noise * 6.0
            )
            _gauges["demo_cache_hit_ratio"] = min(
                1.0, max(0.0, 0.968 - 0.11 * (deg - 1.0) / 4.0 + noise * 0.01)
            )
            _gauges["demo_worker_utilization"] = min(
                1.0, max(0.0, 0.22 + 0.55 * load * deg + noise * 0.1)
            )
        time.sleep(1.0)


# --------------------------------------------------------------------------
# Request handling
# --------------------------------------------------------------------------

def _record(endpoint, status, duration):
    with _lock:
        _requests[(endpoint, str(status))] += 1
        _hist_sum[endpoint] += duration
        _hist_count[endpoint] += 1
        counts = _hist_counts[endpoint]
        for i, b in enumerate(BUCKETS):
            if duration <= b:
                counts[i] += 1
        if status >= 500:
            _errors["5xx"] += 1
        elif status >= 400:
            _errors["4xx"] += 1


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "checkout-api/1.4.2"

    def log_message(self, *args):
        pass  # keep the console readable

    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/metrics":
            self._metrics()
            return

        spec = ROUTES.get(path)
        if spec is None:
            _record("/404", 404, 0.001)
            self._send(404, "not found\n")
            return

        started = time.perf_counter()
        deg = _degrade_factor()

        # simulate the work
        delay = spec["base"] * deg * random.uniform(0.7, 1.45)
        time.sleep(delay)

        # decide the status code
        fail_p = spec["fail"] * deg * 6.0
        r = random.random()
        if r < fail_p:
            status = 500 if r < fail_p * 0.7 else 503
        elif r < fail_p + 0.012:
            status = 404
        else:
            status = 200

        duration = time.perf_counter() - started
        _record(path, status, duration)

        if status >= 500:
            self._send(status, f"upstream error while handling {path}\n")
        elif status == 404:
            self._send(404, "not found\n")
        else:
            self._send(200, f"ok {path} in {duration*1000:.1f}ms\n")

    # -- exposition ------------------------------------------------------

    def _metrics(self):
        out = []
        w = out.append

        w("# HELP demo_build_info Build information.")
        w("# TYPE demo_build_info gauge")
        w('demo_build_info{version="1.4.2",service="checkout-api"} 1')
        w("# HELP demo_up Whether the service is up.")
        w("# TYPE demo_up gauge")
        w(f"demo_up {_gauges['demo_up']}")

        w("# HELP demo_uptime_seconds Seconds since process start.")
        w("# TYPE demo_uptime_seconds gauge")
        w(f"demo_uptime_seconds {time.time() - _started_at:.1f}")

        with _lock:
            w("# HELP demo_http_requests_total Total HTTP requests handled.")
            w("# TYPE demo_http_requests_total counter")
            for (ep, st), n in sorted(_requests.items()):
                w(f'demo_http_requests_total{{endpoint="{ep}",method="GET",status="{st}"}} {n}')

            w("# HELP demo_errors_total Application errors by class.")
            w("# TYPE demo_errors_total counter")
            for kind, n in sorted(_errors.items()):
                w(f'demo_errors_total{{type="{kind}"}} {n}')

            w("# HELP demo_http_request_duration_seconds Request latency.")
            w("# TYPE demo_http_request_duration_seconds histogram")
            for ep in sorted(_hist_count):
                counts = _hist_counts[ep]
                for b, c in zip(BUCKETS, counts):
                    w(f'demo_http_request_duration_seconds_bucket{{endpoint="{ep}",le="{b}"}} {c}')
                w(f'demo_http_request_duration_seconds_bucket{{endpoint="{ep}",le="+Inf"}} {_hist_count[ep]}')
                w(f'demo_http_request_duration_seconds_sum{{endpoint="{ep}"}} {_hist_sum[ep]:.6f}')
                w(f'demo_http_request_duration_seconds_count{{endpoint="{ep}"}} {_hist_count[ep]}')

            for name, val in _gauges.items():
                if name in ("demo_up",):
                    continue
                w(f"# HELP {name} Demo gauge.")
                w(f"# TYPE {name} gauge")
                w(f"{name} {val:.4f}")

        body = "\n".join(out) + "\n"
        payload = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()

    threading.Thread(target=_simulator, daemon=True).start()

    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"checkout-api listening on http://0.0.0.0:{args.port}  (metrics at /metrics)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
