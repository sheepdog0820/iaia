"""Verify Docker's actual ignore rules using synthetic Terraform artifacts."""

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
)
ALLOWED = (
    "infrastructure/terraform/bootstrap/main.tf",
    "infrastructure/terraform/bootstrap/.terraform.lock.hcl",
    "infrastructure/terraform/bootstrap/terraform.tfvars.example",
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
            raise AssertionError(f"Local Terraform artifacts entered the build context: {leaked}")
        for name in ALLOWED:
            assert (exported / name).read_text(encoding="utf-8") == "synthetic-context-fixture\n", name
    print("PASS: Terraform caches, state and local variables excluded; source and examples retained")


if __name__ == "__main__":
    main()
