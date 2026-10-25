#!/usr/bin/env python3
"""Reproducible HTTP load test for the Hoplid order API."""

import argparse
import concurrent.futures
import json
import math
import os
import statistics
import time
import uuid
from urllib.parse import urljoin

import httpx


def percentile(values, p):
    """Return a nearest-rank percentile."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil((p / 100) * len(ordered)) - 1)
    return ordered[index]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.getenv("API_URL", "http://127.0.0.1:8000"),
        help="API base URL (default: API_URL or http://127.0.0.1:8000)",
    )
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    if args.requests < 1 or args.concurrency < 1 or args.timeout <= 0:
        parser.error("--requests and --concurrency must be positive; --timeout must be positive")

    endpoint = urljoin(args.base_url.rstrip("/") + "/", "api/orders")
    run_id = uuid.uuid4().hex
    latencies_ms = []
    statuses = []
    errors = []
    start = time.perf_counter()

    def send_one(index):
        key = f"load-{run_id}-{index}"
        payload = {
            "user_id": f"load-{run_id}-{index}",
            "vendor_id": "load-test-vendor",
            "items": [{"item_id": "load-test-item", "quantity": 1}],
        }
        request_start = time.perf_counter()
        try:
            with httpx.Client(timeout=args.timeout) as client:
                response = client.post(
                    endpoint,
                    headers={"Idempotency-Key": key},
                    json=payload,
                )
            elapsed_ms = (time.perf_counter() - request_start) * 1000
            return {
                "status": response.status_code,
                "latency_ms": elapsed_ms,
                "error": None if 200 <= response.status_code < 300
                else f"HTTP {response.status_code}: {response.text[:200]}",
            }
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - request_start) * 1000
            return {
                "status": None,
                "latency_ms": elapsed_ms,
                "error": f"{type(exc).__name__}: {exc}",
            }

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.concurrency
    ) as executor:
        results = list(executor.map(send_one, range(args.requests)))

    duration_s = time.perf_counter() - start

    for result in results:
        latencies_ms.append(result["latency_ms"])
        statuses.append(result["status"])
        if result["error"]:
            errors.append(result["error"])

    successful = sum(
        status is not None and 200 <= status < 300 for status in statuses
    )
    failed = args.requests - successful
    throughput = args.requests / duration_s if duration_s > 0 else 0.0

    print("\n=== Hoplid API Load Test ===")
    print(f"Endpoint:       {endpoint}")
    print(f"Run ID:         {run_id}")
    print(f"Requests:       {args.requests}")
    print(f"Concurrency:    {args.concurrency}")
    print(f"Duration:       {duration_s:.2f} seconds")
    print(f"Throughput:     {throughput:.2f} requests/second")
    print(f"Successful 2xx: {successful}")
    print(f"Failed:         {failed}")
    print(f"Error rate:     {(failed / args.requests) * 100:.2f}%")
    print(f"Latency p50:    {percentile(latencies_ms, 50):.2f} ms")
    print(f"Latency p95:    {percentile(latencies_ms, 95):.2f} ms")
    print(f"Latency p99:    {percentile(latencies_ms, 99):.2f} ms")

    if errors:
        print("\nSample errors:")
        for error in errors[:10]:
            print(f"- {error}")

    print("\nJSON summary:")
    print(json.dumps({
        "endpoint": endpoint,
        "run_id": run_id,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "duration_seconds": round(duration_s, 3),
        "throughput_requests_per_second": round(throughput, 2),
        "successful_2xx": successful,
        "failed": failed,
        "error_rate_percent": round((failed / args.requests) * 100, 2),
        "latency_ms": {
            "p50": round(percentile(latencies_ms, 50), 2),
            "p95": round(percentile(latencies_ms, 95), 2),
            "p99": round(percentile(latencies_ms, 99), 2),
        },
    }, indent=2))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
