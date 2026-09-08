import fnmatch
import re
from pathlib import Path

from django.test import SimpleTestCase


class BackgroundRemovalInfrastructureTests(SimpleTestCase):
    ROOT = Path(__file__).resolve().parents[2]

    def test_terraform_defines_an_on_demand_background_removal_task(self):
        terraform = (self.ROOT / "infrastructure" / "terraform" / "main.tf").read_text(encoding="utf-8")

        self.assertIn('resource "aws_ecs_task_definition" "background_removal"', terraform)
        self.assertIn('"BACKGROUND_REMOVAL_TASK_DEFINITION"', terraform)
        self.assertIn('"BACKGROUND_REMOVAL_SUBNETS"', terraform)
        self.assertIn('"BACKGROUND_REMOVAL_SECURITY_GROUPS"', terraform)
        self.assertIn('"BACKGROUND_REMOVAL_ASSIGN_PUBLIC_IP"', terraform)
        self.assertIn('"BACKGROUND_REMOVAL_JOB_TIMEOUT_SECONDS"', terraform)
        self.assertIn('"background-removal"', terraform)
        self.assertIn("cpu                      = var.background_removal_cpu", terraform)
        self.assertIn("memory                   = var.background_removal_memory", terraform)

    def test_web_task_role_can_only_launch_the_dedicated_worker(self):
        terraform = (self.ROOT / "infrastructure" / "terraform" / "main.tf").read_text(encoding="utf-8")

        self.assertIn('resource "aws_iam_role_policy" "background_removal_launcher"', terraform)
        self.assertIn('Action   = ["ecs:RunTask"]', terraform)
        self.assertIn("Resource = aws_ecs_task_definition.background_removal.arn", terraform)
        self.assertIn('"iam:PassedToService"', terraform)
        self.assertIn('"ecs-tasks.amazonaws.com"', terraform)

    def test_background_removal_capacity_defaults_match_the_runbook(self):
        variables = (self.ROOT / "infrastructure" / "terraform" / "variables.tf").read_text(encoding="utf-8")

        self.assertRegex(
            variables,
            re.compile(r'variable "background_removal_cpu"\s*\{.*?default\s*=\s*1024', re.DOTALL),
        )
        self.assertRegex(
            variables,
            re.compile(r'variable "background_removal_memory"\s*\{.*?default\s*=\s*2048', re.DOTALL),
        )

    def test_cloudfront_cannot_fetch_private_background_removal_files(self):
        terraform = (self.ROOT / "infrastructure" / "terraform" / "main.tf").read_text(encoding="utf-8")
        statement = terraform.split('Sid       = "DenyPublicPrivateMediaDownloads"', 1)[1].split("Condition =", 1)[0]
        self.assertIn('Effect    = "Deny"', statement)
        self.assertIn('Principal = { Service = "cloudfront.amazonaws.com" }', statement)
        self.assertIn('Action    = "s3:GetObject"', statement)
        patterns = re.findall(r'"\$\{aws_s3_bucket.assets.arn\}/([^"\n]+)"', statement)
        for prefix in ("", "media/", "custom/media/"):
            for suffix in ("input/source.png", "output/result.png"):
                key = f"{prefix}background_removal/{suffix}"
                with self.subTest(key=key):
                    self.assertTrue(any(fnmatch.fnmatchcase(key, pattern) for pattern in patterns))
        for key in ("static/app.css", "media/profiles/avatar.png", "media/character_images/portrait.png"):
            with self.subTest(public_key=key):
                self.assertFalse(any(fnmatch.fnmatchcase(key, pattern) for pattern in patterns))
