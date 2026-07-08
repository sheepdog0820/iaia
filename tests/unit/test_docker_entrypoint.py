from pathlib import Path

import yaml
from django.test import SimpleTestCase


class DockerEntrypointTests(SimpleTestCase):
    ROOT = Path(__file__).resolve().parents[2]

    def test_default_server_command_executes_daphne(self):
        lines = (self.ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8").splitlines()

        daphne_lines = [line for line in lines if "exec daphne" in line]

        self.assertEqual(daphne_lines, ["exec daphne \\"])
        self.assertIn("  --bind 0.0.0.0 \\", lines)
        self.assertIn("  --port 8000 \\", lines)
        self.assertIn('  "${DJANGO_ASGI_MODULE:-tableno.asgi}:application"', lines)

    def test_entrypoint_does_not_auto_migrate_outside_local_defaults(self):
        content = (self.ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")

        self.assertIn("is_local_env() {", content)
        self.assertIn('case "${APP_ENV:-local}" in', content)
        self.assertIn('if [ -z "${RUN_MIGRATIONS+x}" ] && [ "$#" -eq 0 ] && is_local_env; then', content)
        self.assertIn('if [ -z "${RUN_COLLECTSTATIC+x}" ] && [ "$#" -eq 0 ] && is_local_env; then', content)
        self.assertIn('if is_true "${RUN_MIGRATIONS:-false}"; then', content)
        self.assertIn('if is_true "${RUN_COLLECTSTATIC:-false}"; then', content)

    def test_entrypoint_can_create_development_login_user(self):
        content = (self.ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")

        self.assertIn('if is_true "${CREATE_DEV_LOGIN_USER:-false}"; then', content)
        self.assertIn("DEV_LOGIN_USERNAME is required when CREATE_DEV_LOGIN_USER is true", content)
        self.assertIn("DEV_LOGIN_PASSWORD is required when CREATE_DEV_LOGIN_USER is true", content)
        self.assertIn("python manage.py ensure_dev_login_user \\", content)
        self.assertIn('--username "${DEV_LOGIN_USERNAME}" \\', content)
        self.assertIn('--password "${DEV_LOGIN_PASSWORD}" \\', content)

    def test_collectstatic_failure_tolerance_is_local_only_by_default(self):
        content = (self.ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")

        self.assertIn('if [ -z "${COLLECTSTATIC_ALLOW_FAILURE+x}" ] && is_local_env; then', content)
        self.assertIn("COLLECTSTATIC_ALLOW_FAILURE=true", content)
        self.assertIn('if is_true "${COLLECTSTATIC_ALLOW_FAILURE:-false}"; then', content)
        self.assertIn("python manage.py collectstatic --noinput || true", content)
        self.assertIn("else\n    python manage.py collectstatic --noinput", content)

    def test_aws_pre_runbook_documents_explicit_migration_tasks(self):
        runbook = (self.ROOT / "docs/release/AWS_PRE_RELEASE_RUNBOOK.md").read_text(encoding="utf-8")

        self.assertIn("usually does not run migration automatically", runbook)
        self.assertIn("python manage.py migrate --noinput", runbook)
        self.assertIn("python manage.py collectstatic --noinput", runbook)
        self.assertIn("RUN_MIGRATIONS=true", runbook)
        self.assertIn("RUN_COLLECTSTATIC=true", runbook)
        self.assertNotIn("entrypoint.sh` runs `python manage.py migrate --noinput` at startup", runbook)
        self.assertNotIn("起動時に `python manage.py migrate --noinput` を実行します", runbook)

    def test_entrypoint_comment_lines_are_ascii(self):
        lines = (self.ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8").splitlines()

        for line in lines:
            if line.lstrip().startswith("#"):
                try:
                    line.encode("ascii")
                except UnicodeEncodeError as exc:
                    raise AssertionError(f"entrypoint comment is not ASCII: {line!r}") from exc

    def test_compose_files_keep_app_env_file_separate(self):
        compose = (self.ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        mysql_compose = (self.ROOT / "docker-compose.mysql.yml").read_text(encoding="utf-8")

        self.assertIn("- ${ENV_FILE:-.env.development}", compose)
        self.assertIn("- ${ENV_FILE:-.env.production}", mysql_compose)
        self.assertIn("APP_ENV: ${APP_ENV:-aws-prod}", mysql_compose)
        self.assertIn("DB_ENGINE: mysql", mysql_compose)
        self.assertNotIn("SECRET_KEY:", compose)
        self.assertNotIn("STRIPE_SECRET_KEY:", compose)
        self.assertNotIn("SECRET_KEY:", mysql_compose)
        self.assertNotIn("STRIPE_SECRET_KEY:", mysql_compose)

    def test_compose_interpolation_example_contains_no_app_secrets(self):
        env_example = (self.ROOT / ".env.compose.example").read_text(encoding="utf-8")
        allowed_prefixes = {
            "APP_ENV",
            "ENV_FILE",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
        }

        for line in env_example.splitlines():
            if not line or line.startswith("#"):
                continue
            key = line.split("=", 1)[0]
            self.assertIn(key, allowed_prefixes)

        self.assertIn("ENV_FILE=.env.docker.example", env_example)
        self.assertNotIn("SECRET_KEY", env_example)
        self.assertNotIn("STRIPE_", env_example)
        self.assertNotIn("GOOGLE_", env_example)
        self.assertNotIn("DISCORD_", env_example)

    def test_docker_env_example_is_compose_safe(self):
        docker_env = (self.ROOT / ".env.docker.example").read_text(encoding="utf-8")

        required_lines = [
            "SECRET_KEY=docker-compose-example-secret-key-without-dollar-sign",
            "DB_ENGINE=postgres",
            "DB_HOST=db",
            "STRIPE_CHECKOUT_ENABLED=False",
            "PUBLIC_SITE_URL=http://127.0.0.1:8000",
        ]
        for line in required_lines:
            self.assertIn(line, docker_env)
        self.assertNotIn("$", docker_env)

    def test_qnap_compose_env_example_documents_dev_login(self):
        qnap_compose = (self.ROOT / "docker-compose.qnap.yml").read_text(encoding="utf-8")
        qnap_env = (self.ROOT / ".env.qnap.example").read_text(encoding="utf-8")

        self.assertIn("postgres:16", qnap_compose)
        self.assertIn("${WEB_PORT:-8000}:8000", qnap_compose)
        self.assertIn("ENV_FILE: ${ENV_FILE:-.env.qnap}", qnap_compose)
        self.assertIn("CREATE_DEV_LOGIN_USER=True", qnap_env)
        self.assertIn("DEV_LOGIN_USERNAME=testuser", qnap_env)
        self.assertIn("DEV_LOGIN_PASSWORD=change-this-test-password", qnap_env)
        self.assertIn("NAS-CTHULHU", qnap_env)
        self.assertNotIn("sk_live_", qnap_env)

    def test_gitignore_keeps_compose_env_local_but_tracks_example(self):
        gitignore = (self.ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn(".env*", gitignore)
        self.assertIn("!.env*.example", gitignore)

    def test_compose_dollar_interpolation_warning_is_documented(self):
        readme = (self.ROOT / "README.md").read_text(encoding="utf-8")
        docker_setup = (self.ROOT / "docs/setup/DOCKER_SETUP.md").read_text(encoding="utf-8")
        env_example = (self.ROOT / ".env.example").read_text(encoding="utf-8")

        for content in (readme, docker_setup):
            self.assertIn("env_file", content)
            self.assertIn("$$", content)
            self.assertIn("SECRET_KEY", content)
            self.assertIn(".env.compose", content)
            self.assertIn(".env.docker.example", content)

        self.assertIn("env_file", env_example)
        self.assertIn("$$", env_example)
        self.assertNotIn("SECRET_KEY=your-production-secret-key-here-change-this", env_example)

    def load_ci_workflow(self):
        workflow_path = self.ROOT / ".github" / "workflows" / "django-ci.yml"
        with workflow_path.open(encoding="utf-8") as stream:
            return yaml.safe_load(stream)

    def test_ci_workflow_yaml_has_expected_steps_in_order(self):
        workflow = self.load_ci_workflow()
        steps = workflow["jobs"]["test"]["steps"]
        step_names = [step.get("name") or step.get("uses") for step in steps]

        expected_order = [
            "actions/checkout@v4",
            "actions/setup-python@v5",
            "Install dependencies",
            "Django check",
            "Migration file check",
            "Migration apply/check",
            "Run pytest",
            "Flake8",
            "Black check",
            "isort check",
            "Docker Compose config check",
            "Django deploy check",
            "Billing release gate",
        ]
        self.assertEqual(step_names, expected_order)

    def test_ci_workflow_yaml_parser_dependency_is_declared(self):
        requirements_test = (self.ROOT / "requirements-test.txt").read_text(encoding="utf-8")

        self.assertIn("PyYAML>=6.0.0", requirements_test)

    def test_ci_runs_compose_config_check(self):
        workflow = (self.ROOT / ".github" / "workflows" / "django-ci.yml").read_text(encoding="utf-8")

        self.assertIn("Docker Compose config check", workflow)
        self.assertIn("ENV_FILE: .env.example", workflow)
        self.assertIn("DB_PASSWORD: placeholder-db-password", workflow)
        self.assertIn("DB_ROOT_PASSWORD: placeholder-root-password", workflow)
        self.assertIn("docker compose --env-file .env.compose.example config --quiet", workflow)
        self.assertIn(
            "docker compose --env-file .env.compose.example -f docker-compose.mysql.yml config --quiet",
            workflow,
        )
        self.assertIn("Django deploy check", workflow)
        self.assertIn("DJANGO_SETTINGS_MODULE: tableno.settings_production", workflow)
        self.assertIn("python manage.py check --deploy", workflow)

    def test_ci_runs_billing_release_gate(self):
        workflow = (self.ROOT / ".github" / "workflows" / "django-ci.yml").read_text(encoding="utf-8")

        self.assertIn("Billing release gate", workflow)
        self.assertIn('STRIPE_CHECKOUT_ENABLED: "False"', workflow)
        self.assertIn("python manage.py billing_release_gate", workflow)
        self.assertLess(
            workflow.index("Run pytest"),
            workflow.index("Billing release gate"),
        )

    def test_python_version_is_consistent_for_release_paths(self):
        dockerfile = (self.ROOT / "Dockerfile").read_text(encoding="utf-8")
        workflow = (self.ROOT / ".github" / "workflows" / "django-ci.yml").read_text(encoding="utf-8")
        docs_to_check = [
            self.ROOT / "README.md",
            self.ROOT / "docs/setup/DOCKER_SETUP.md",
            self.ROOT / "AGENTS.md",
            self.ROOT / "CLAUDE.md",
            self.ROOT / "docs/specifications/PROJECT_SPECIFICATION.md",
        ]
        python_version_file = self.ROOT / ".python-version"

        self.assertIn("FROM python:3.11-slim", dockerfile)
        self.assertIn('python-version: "3.11"', workflow)
        self.assertNotIn("python:3.10", dockerfile)
        self.assertNotIn('python-version: "3.10"', workflow)
        for doc_path in docs_to_check:
            content = doc_path.read_text(encoding="utf-8")
            self.assertRegex(content, r"Python:? 3\.11\+", f"{doc_path.name} must document Python 3.11+")
            self.assertNotIn("Python 3.10", content, f"{doc_path.name} must not document Python 3.10")
        self.assertTrue(python_version_file.exists())
        self.assertRegex(python_version_file.read_text(encoding="utf-8").strip(), r"^3\.11(\.|$)")
