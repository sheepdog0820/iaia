"""Measure read-only endpoint latency; this does not certify release performance."""

import argparse
import concurrent.futures
import json
import math
import os
import time
from urllib.parse import urlsplit

import requests


def measure(base_url, path, token, timeout):
    started = time.perf_counter()
    headers = {"Authorization": f"Token {token}"} if token else {}
    try:
        with requests.get(
            base_url.rstrip("/") + path, headers=headers, timeout=timeout, allow_redirects=False
        ) as response:
            status = response.status_code
            error = None
    except requests.RequestException as exc:
        status, error = 0, type(exc).__name__
    return {"path": path, "status": status, "error": error, "ms": (time.perf_counter() - started) * 1000}


def summarize(rows):
    summaries = []
    for path in sorted({row["path"] for row in rows}):
        selected = [row for row in rows if row["path"] == path]
        times = sorted(row["ms"] for row in selected)
        summaries.append(
            {
                "path": path,
                "requests": len(selected),
                "successes": sum(row["status"] == 200 for row in selected),
                "statuses": {
                    str(code): sum(row["status"] == code for row in selected)
                    for code in sorted({r["status"] for r in selected})
                },
                "errors": sorted({row["error"] for row in selected if row["error"]}),
                "p50_ms": times[math.ceil(len(times) * 0.50) - 1],
                "p95_ms": times[math.ceil(len(times) * 0.95) - 1],
                "p99_ms": times[math.ceil(len(times) * 0.99) - 1],
                "max_ms": times[-1],
            }
        )
    return {"qualification": "not_evaluated", "latency_includes_errors": True, "endpoints": summaries}


def run(args):
    parsed = urlsplit(args.base_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Base URL must be HTTP(S) without credentials")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("Base URL must contain only the origin")
    if args.requests < 1 or args.concurrency < 1 or args.timeout <= 0:
        raise ValueError("Request count, concurrency and timeout must be positive")
    if not args.path or any(not path.startswith("/") or path.startswith("//") or "#" in path for path in args.path):
        raise ValueError("Provide origin-relative endpoint paths")
    tokens = json.loads(os.environ.get("TABLENO_LOAD_TOKENS", "[]"))
    if not isinstance(tokens, list) or any(not isinstance(token, str) or not token for token in tokens):
        raise ValueError("TABLENO_LOAD_TOKENS must be a JSON array of nonempty token strings")
    tokens = tokens or [None]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [
            pool.submit(measure, args.base_url, path, tokens[index % len(tokens)], args.timeout)
            for index in range(args.requests)
            for path in args.path
        ]
        rows = [future.result() for future in concurrent.futures.as_completed(futures)]
    result = summarize(rows)
    result.update({"concurrency": args.concurrency, "identities": len(tokens), "authenticated": tokens != [None]})
    print(json.dumps(result, ensure_ascii=False))
    return 0 if all(row["status"] == 200 for row in rows) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--requests", type=int, default=30, help="Requests per endpoint")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=10)
    raise SystemExit(run(parser.parse_args()))
