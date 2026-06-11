"""Plan or execute a local media directory sync to S3."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import boto3


def md5(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - S3 ETag comparison for non-multipart files.
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_plan(root: Path, bucket: str, prefix: str, client) -> list[tuple[str, Path, str]]:
    plan = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        key = f"{prefix.strip('/')}/{relative}".lstrip("/")
        action = "upload"
        try:
            remote = client.head_object(Bucket=bucket, Key=key)
            if remote.get("ETag", "").strip('"') == md5(path):
                action = "skip"
        except client.exceptions.ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 404:
                raise
        plan.append((action, path, key))
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("media"))
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", default="media")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if not args.source.is_dir():
        parser.error(f"source directory not found: {args.source}")

    client = boto3.client("s3", region_name=os.getenv("AWS_REGION", "ap-northeast-1"))
    plan = build_plan(args.source, args.bucket, args.prefix, client)
    for action, path, key in plan:
        print(f"{action.upper():6} {path} -> s3://{args.bucket}/{key}")
        if action == "upload" and args.execute:
            client.upload_file(str(path), args.bucket, key)
    uploads = sum(1 for action, _, _ in plan if action == "upload")
    print(f"planned_uploads={uploads} total_files={len(plan)} execute={args.execute}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
