"""Verify Docker's actual ignore rules using synthetic local artifacts."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = (
    ".terraform/providers/provider.exe",
    "infrastructure/terraform/.terraform/providers/provider.exe",
    "infrastructure/terraform/bootstrap/.terraform/providers/provider.exe",
    "infrastructure/terraform/environments/nested/.terraform/providers/provider.exe",
    "terraform.tfstate",
    "infrastructure/terraform/bootstrap/terraform.tfstate",
    "infrastructure/terraform/bootstrap/terraform.tfstate.backup",
    "infrastructure/terraform/bootstrap/local.tfvars",
    "infrastructure/terraform/bootstrap/local.auto.tfvars.json",
    "__pycache__/cache-marker.txt",
    "accounts/__pycache__/models.cpython-311.pyc",
    "tests/unit/__pycache__/test_example.cpython-311-pytest-9.1.1.pyc",
    "tests/unit/__pycache__/cache-marker.txt",
    "module.pyc",
    "accounts/module.pyc",
    "tests/unit/module.pyo",
    "tests/unit/module.pyd",
    ".pytest_cache/v/cache/nodeids",
    "tests/.pytest_cache/v/cache/nodeids",
    "tests/unit/.pytest_cache/v/cache/nodeids",
)
ALLOWED = (
    "infrastructure/terraform/bootstrap/main.tf",
    "infrastructure/terraform/bootstrap/.terraform.lock.hcl",
    "infrastructure/terraform/bootstrap/terraform.tfvars.example",
    "manage.py",
    "accounts/models.py",
    "tests/unit/test_example.py",
    "requirements.lock.txt",
    "templates/accounts/character_detail.html",
    "static/js/session_images.js",
    "README.md",
)


def main():
    temporary_root = (ROOT / "tmp").resolve()
    if temporary_root.parent != ROOT:
        raise RuntimeError("Temporary build context must remain inside the repository")
    temporary_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="docker-context-check-", dir=temporary_root) as directory:
        scratch = Path(directory).resolve()
        context = scratch / "context"
        output = scratch / "export"
        context.mkdir()
        shutil.copyfile(ROOT / ".dockerignore", context / ".dockerignore")
        (context / "Dockerfile").write_text("FROM scratch\nCOPY . /context\n", encoding="utf-8")
        for name in FORBIDDEN + ALLOWED:
            fixture = context / name
            fixture.parent.mkdir(parents=True, exist_ok=True)
            fixture.write_text("synthetic-context-fixture\n", encoding="utf-8")
        subprocess.run(
            ["docker", "build", "--network", "none", "--output", f"type=local,dest={output}", str(context)],
            env={**os.environ, "DOCKER_BUILDKIT": "1"},
            check=True,
        )
        exported = output / "context"
        leaked = [name for name in FORBIDDEN if (exported / name).exists()]
        if leaked:
            raise AssertionError(f"Local artifacts entered the build context: {leaked}")
        for name in ALLOWED:
            assert (exported / name).read_text(encoding="utf-8") == "synthetic-context-fixture\n", name
    print("PASS: Terraform artifacts and Python caches excluded; source, assets and examples retained")


if __name__ == "__main__":
    main()
