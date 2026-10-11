#!/usr/bin/env python3
"""
loadgen -- drives realistic traffic at the demo checkout-api.

Traffic mix and intensity vary over time so the dashboards show believable
curves instead of flat lines. Every request is a real HTTP request.

Run:  python loadgen.py --url http://127.0.0.1:8080 --rps 18
"""

import argparse
import random
import threading
import time
import urllib.error
import urllib.request

# realistic mix: reads dominate, expensive reports are rare
MIX = [
    ("/api/cart", 34),
    ("/api/search", 26),
    ("/health", 18),
    ("/", 10),
    ("/api/checkout", 9),
    ("/api/report", 3),
]

_stop = threading.Event()


def _pick():
    total = sum(w for _, w in MIX)
    r = random.uniform(0, total)
    upto = 0.0
    for path, w in MIX:
        upto += w
        if r <= upto:
            return path
    return MIX[0][0]


def worker(base_url, interval, stats, lock):
    while not _stop.is_set():
        path = _pick()
        url = base_url + path
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                resp.read()
                code = resp.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception:
            code = 0
        with lock:
            stats[code] = stats.get(code, 0) + 1
        # small jitter so threads do not synchronise
        time.sleep(interval * random.uniform(0.6, 1.4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--rps", type=float, default=18.0, help="target requests per second")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    # 8 minute intensity cycle, matching the demo service's load curve
    interval = args.workers / max(args.rps, 0.1)
    stats, lock = {}, threading.Lock()
    threads = [
        threading.Thread(target=worker, args=(args.url, interval, stats, lock), daemon=True)
        for _ in range(args.workers)
    ]
    for t in threads:
        t.start()

    print(f"loadgen -> {args.url}  workers={args.workers}  target_rps={args.rps}")
    try:
        last = time.time()
        while True:
            time.sleep(20)
            now = time.time()
            with lock:
                n = sum(stats.values())
                snapshot = dict(stats)
            print(f"  sent={n}  last_{int(now-last)}s_rps={n/(now-last):.1f}  status={snapshot}")
            last = now
    except KeyboardInterrupt:
        _stop.set()


if __name__ == "__main__":
    main()
