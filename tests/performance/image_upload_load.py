#!/usr/bin/env python
"""
HTTP image upload load probe for release checks.

Examples:
  python tests/performance/image_upload_load.py --base-url http://127.0.0.1:8000 --dev-login admin
  TABLENO_USERNAME=user TABLENO_PASSWORD=... python tests/performance/image_upload_load.py --base-url https://stg.tableno.jp
"""

from __future__ import annotations

import argparse
import concurrent.futures
import io
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin

import requests
from PIL import Image


class CsrfParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.csrf_token = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "input":
            return
        values = dict(attrs)
        if values.get("name") == "csrfmiddlewaretoken":
            self.csrf_token = values.get("value") or ""


@dataclass(frozen=True)
class ProbeResult:
    name: str
    status_code: int
    elapsed_ms: float
    ok: bool
    detail: str


def absolute_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def extract_csrf(html: str) -> str:
    parser = CsrfParser()
    parser.feed(html)
    if not parser.csrf_token:
        raise RuntimeError("csrf token not found")
    return parser.csrf_token


def csrf_header(session: requests.Session) -> dict[str, str]:
    token = session.cookies.get("csrftoken")
    return {"X-CSRFToken": token} if token else {}


def make_image_bytes(image_format: str, target_size: int, color: tuple[int, int, int]) -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (128, 128), color=color)
    image.save(buffer, image_format)
    payload = buffer.getvalue()
    if len(payload) < target_size:
        payload += b"\0" * (target_size - len(payload))
    return payload


def login(base_url: str, args: argparse.Namespace) -> requests.Session:
    session = requests.Session()

    if args.dev_login:
        login_url = absolute_url(base_url, "/accounts/dev-login/?next=/")
        response = session.get(login_url, timeout=args.timeout)
        response.raise_for_status()
        csrf = extract_csrf(response.text)
        response = session.post(
            absolute_url(base_url, "/accounts/dev-login/"),
            data={
                "username": args.dev_login,
                "csrfmiddlewaretoken": csrf,
                "next": "/",
            },
            headers={"Referer": login_url},
            allow_redirects=True,
            timeout=args.timeout,
        )
        response.raise_for_status()
        return session

    username = args.username or os.environ.get("TABLENO_USERNAME")
    password = args.password or os.environ.get("TABLENO_PASSWORD")
    if not username or not password:
        raise RuntimeError("provide --dev-login or TABLENO_USERNAME/TABLENO_PASSWORD")

    login_url = absolute_url(base_url, "/login/")
    response = session.get(login_url, timeout=args.timeout)
    response.raise_for_status()
    csrf = extract_csrf(response.text)
    response = session.post(
        login_url,
        data={
            "username": username,
            "password": password,
            "csrfmiddlewaretoken": csrf,
        },
        headers={"Referer": login_url},
        allow_redirects=True,
        timeout=args.timeout,
    )
    response.raise_for_status()
    if "/login/" in response.url or "/accounts/login/" in response.url:
        raise RuntimeError("login did not leave login page")
    return session


def post_json(session: requests.Session, base_url: str, path: str, payload: dict, timeout: float) -> dict:
    response = session.post(
        absolute_url(base_url, path),
        json=payload,
        headers=csrf_header(session),
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def create_fixtures(session: requests.Session, base_url: str, timeout: float) -> dict:
    suffix = int(time.time() * 1000)
    group = post_json(
        session,
        base_url,
        "/api/accounts/groups/",
        {"name": f"Load Probe Group {suffix}", "visibility": "private"},
        timeout,
    )
    scenario = post_json(
        session,
        base_url,
        "/api/scenarios/scenarios/",
        {
            "title": f"Load Probe Scenario {suffix}",
            "author": "release-check",
            "summary": "Image upload load probe fixture.",
            "game_system": "coc",
            "difficulty": "beginner",
            "estimated_duration": "short",
        },
        timeout,
    )
    session_obj = post_json(
        session,
        base_url,
        "/api/schedules/sessions/",
        {
            "title": f"Load Probe Session {suffix}",
            "date": "2030-01-01T19:00:00Z",
            "group": group["id"],
            "duration_minutes": 120,
            "location": "Online",
            "visibility": "group",
            "description": "Image upload load probe fixture.",
        },
        timeout,
    )
    character = post_json(
        session,
        base_url,
        "/api/accounts/character-sheets/create_6th_edition/",
        {
            "name": f"Load Probe Investigator {suffix}",
            "player_name": "release-check",
            "age": 30,
            "str_value": 10,
            "con_value": 11,
            "pow_value": 12,
            "dex_value": 13,
            "app_value": 10,
            "siz_value": 11,
            "int_value": 14,
            "edu_value": 15,
        },
        timeout,
    )
    return {"group": group, "scenario": scenario, "session": session_obj, "character": character}


def cloned_session(auth_session: requests.Session) -> requests.Session:
    session = requests.Session()
    session.cookies.update(auth_session.cookies)
    return session


def upload_once(
    auth_session: requests.Session,
    base_url: str,
    name: str,
    path: str,
    data: dict,
    field_name: str,
    filename: str,
    content: bytes,
    content_type: str,
    expected_statuses: set[int],
    timeout: float,
) -> ProbeResult:
    session = cloned_session(auth_session)
    started = time.perf_counter()
    try:
        response = session.post(
            absolute_url(base_url, path),
            data=data,
            files={field_name: (filename, content, content_type)},
            headers=csrf_header(session),
            timeout=timeout,
        )
        elapsed = (time.perf_counter() - started) * 1000
        ok = response.status_code in expected_statuses
        detail = response.text[:200].replace("\n", " ")
        return ProbeResult(name, response.status_code, elapsed, ok, detail)
    except Exception as exc:
        elapsed = (time.perf_counter() - started) * 1000
        return ProbeResult(name, 0, elapsed, False, repr(exc))


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100) * (len(ordered) - 1)))))
    return ordered[index]


def summarize(results: Iterable[ProbeResult]) -> bool:
    grouped: dict[str, list[ProbeResult]] = {}
    for result in results:
        grouped.setdefault(result.name, []).append(result)

    all_ok = True
    for name, rows in grouped.items():
        latencies = [row.elapsed_ms for row in rows]
        ok_count = sum(1 for row in rows if row.ok)
        all_ok = all_ok and ok_count == len(rows)
        statuses: dict[int, int] = {}
        for row in rows:
            statuses[row.status_code] = statuses.get(row.status_code, 0) + 1
        print(
            json.dumps(
                {
                    "probe": name,
                    "ok": ok_count,
                    "total": len(rows),
                    "statuses": statuses,
                    "avg_ms": round(statistics.mean(latencies), 1),
                    "p95_ms": round(percentile(latencies, 95), 1),
                    "max_ms": round(max(latencies), 1),
                },
                ensure_ascii=False,
            )
        )
        for row in rows:
            if not row.ok:
                print(f"FAIL {row.name} status={row.status_code} detail={row.detail}", file=sys.stderr)
    return all_ok


def run(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    auth_session = login(base_url, args)
    fixtures = create_fixtures(auth_session, base_url, args.timeout)

    one_mb = 1024 * 1024
    five_mb = 5 * 1024 * 1024
    oversized = five_mb + 1
    image_cases = [
        ("jpg-1mb", "JPEG", "image/jpeg", "probe-1mb.jpg", one_mb, {201}),
        ("jpg-5mb", "JPEG", "image/jpeg", "probe-5mb.jpg", five_mb, {201}),
        ("jpg-oversize", "JPEG", "image/jpeg", "probe-oversize.jpg", oversized, {400}),
        ("png-1mb", "PNG", "image/png", "probe-1mb.png", one_mb, {201}),
        ("png-5mb", "PNG", "image/png", "probe-5mb.png", five_mb, {201}),
        ("png-oversize", "PNG", "image/png", "probe-oversize.png", oversized, {400}),
        ("gif-1mb", "GIF", "image/gif", "probe-1mb.gif", one_mb, {201}),
        ("gif-5mb", "GIF", "image/gif", "probe-5mb.gif", five_mb, {201}),
        ("gif-oversize", "GIF", "image/gif", "probe-oversize.gif", oversized, {400}),
    ]

    tasks = []
    for index in range(args.requests_per_target):
        image_name, image_format, content_type, filename, target_size, expected = image_cases[index % len(image_cases)]
        content = make_image_bytes(image_format, target_size, (index % 255, 20, 180))
        tasks.extend(
            [
                (
                    f"character-{image_name}",
                    f"/api/accounts/character-sheets/{fixtures['character']['id']}/images/",
                    {},
                    "image",
                    filename,
                    content,
                    content_type,
                    expected,
                ),
                (
                    f"scenario-{image_name}",
                    "/api/scenarios/scenario-images/",
                    {"scenario": str(fixtures["scenario"]["id"]), "title": filename},
                    "image",
                    filename,
                    content,
                    content_type,
                    expected,
                ),
                (
                    f"session-{image_name}",
                    "/api/schedules/session-images/",
                    {"session": str(fixtures["session"]["id"]), "title": filename},
                    "image",
                    filename,
                    content,
                    content_type,
                    expected,
                ),
            ]
        )

    results: list[ProbeResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(
                upload_once,
                auth_session,
                base_url,
                task[0],
                task[1],
                task[2],
                task[3],
                task[4],
                task[5],
                task[6],
                task[7],
                args.timeout,
            )
            for task in tasks
        ]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    return 0 if summarize(results) else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Tableno image upload load probe.")
    parser.add_argument("--base-url", default=os.environ.get("TABLENO_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--dev-login", default=os.environ.get("TABLENO_DEV_LOGIN"))
    parser.add_argument("--username", default=os.environ.get("TABLENO_USERNAME"))
    parser.add_argument("--password", default=os.environ.get("TABLENO_PASSWORD"))
    parser.add_argument("--concurrency", type=int, default=int(os.environ.get("TABLENO_LOAD_CONCURRENCY", "4")))
    parser.add_argument(
        "--requests-per-target",
        type=int,
        default=int(os.environ.get("TABLENO_LOAD_REQUESTS_PER_TARGET", "9")),
        help="Number of uploads per target. Keep <= 10 for character image limits.",
    )
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("TABLENO_LOAD_TIMEOUT", "30")))
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
