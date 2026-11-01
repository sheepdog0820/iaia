"""Synthetic document/CLI tests; these fixtures are not Stripe acceptance evidence."""

import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings

from accounts.management.commands.billing_preflight import REQUIRED_WEBHOOK_EVENTS
from accounts.management.commands.billing_release_gate import Command


@override_settings(
    STRIPE_CHECKOUT_ENABLED=True,
    BILLING_EMAIL_DELIVERY_ENABLED=True,
    CELERY_BEAT_SCHEDULE={"billing": {"task": "accounts.tasks.dispatch_billing_emails"}},
)
class BillingReleaseDecisionTests(SimpleTestCase):
    def _record(self, decision):
        return "\n".join(
            [
                "# Synthetic billing gate fixture",
                "| Stripe mode | test |",
                "| Stripe Checkout enabled | yes |",
                "| Expected Stripe Price currency | jpy |",
                "| Expected monthly unit amount | 480 |",
                "| Expected yearly unit amount | 4800 |",
                "billing_stripe_remote_check=ok",
                "recent_event_ids: evt_synthetic_gate_fixture",
                "recent_cancel_at_period_end_event_ids: evt_synthetic_cancel_fixture",
                "cancel_at_period_end=true",
                "StripeWebhookEvent PremiumSubscription Premium audit logs",
                *REQUIRED_WEBHOOK_EVENTS,
                decision,
            ]
        )

    def _command(self, content, output):
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / "synthetic-record.md"
            record.write_text(content, encoding="utf-8")
            call_command(
                "billing_release_gate",
                "--require-paid-checkout",
                verification_record=str(record),
                stdout=output,
            )

    def test_cli_rejects_explicit_no_go_even_when_all_evidence_markers_exist(self):
        output = StringIO()
        with self.assertRaisesMessage(CommandError, "最終判定"):
            self._command(self._record("## 判定\n| 判定 | No-Go |"), output)
        self.assertNotIn("billing_release_gate=ok", output.getvalue())

    def test_cli_accepts_one_explicit_final_go(self):
        output = StringIO()
        self._command(self._record("## 判定\n| 項目 | 値 |\n| --- | --- |\n| 判定 | Go |"), output)
        self.assertIn("billing_release_gate=ok checkout-verified", output.getvalue())

    def test_missing_record_cannot_produce_a_success_marker(self):
        output = StringIO()
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesMessage(CommandError, "not found"):
            call_command(
                "billing_release_gate",
                "--require-paid-checkout",
                verification_record=str(Path(directory) / "absent.md"),
                stdout=output,
            )
        self.assertNotIn("billing_release_gate=ok", output.getvalue())

    def test_missing_blank_conditional_or_template_decisions_are_rejected(self):
        for section in (
            "",
            "| 判定 | Go |",
            "## 判定",
            "## 判定\n| 判定 | |",
            "## 判定\n| 判定 | 条件付きGo |",
            "## 判定\n| 判定 | Go / No-Go / 条件付きGo |",
            "## 判定\n| 判定 | go |",
            "## 判定\n| 判定 | **Go** |",
            "## 判定\n| 判定 | Go | extra |",
        ):
            with self.subTest(section=section):
                self.assertTrue(Command()._validate_record(self._record(section)))

    def test_duplicate_or_conflicting_decisions_are_rejected(self):
        for section in (
            "## 判定\n| 判定 | Go |\n| 判定 | Go |",
            "## 判定\n| 判定 | Go |\n| 判定 | No-Go |",
            "## 判定\n| 判定 | No-Go |\n| 判定 | Go |",
            "## 判定\n| 判定 | Go |\n## 判定\n| 判定 | Go |",
            "## 判定\n| 判定 | Go |\n## 判定",
        ):
            with self.subTest(section=section):
                self.assertTrue(Command()._validate_record(self._record(section)))

    def test_samples_comments_quotes_and_indented_code_are_not_a_final_go(self):
        for section in (
            "```markdown\n## 判定\n| 判定 | Go |\n```",
            "~~~markdown\n## 判定\n| 判定 | Go |\n~~~",
            "<!--\n## 判定\n| 判定 | Go |\n-->",
            "<!--\n## 判定\n| 判定 | Go |",
            "> ## 判定\n> | 判定 | Go |",
            "    ## 判定\n    | 判定 | Go |",
            "\t## 判定\n\t| 判定 | Go |",
            "## 判定\n    | 判定 | Go |",
            "## 別の節\n| 判定 | Go |",
            "## 判定\n## 別の節\n| 判定 | Go |",
            "## 判定\n# 別の節\n| 判定 | Go |",
        ):
            with self.subTest(section=section):
                self.assertTrue(Command()._validate_record(self._record(section)))

    def test_final_no_go_cannot_be_overridden_by_a_go_example(self):
        sample = "```\n## 判定\n| 判定 | Go |\n```\n## 判定\n| 判定 | No-Go |"
        self.assertTrue(Command()._validate_record(self._record(sample)))

    def test_valid_go_can_follow_examples_and_comments(self):
        for example in (
            "```markdown\n## 判定\n| 判定 | No-Go |\n```",
            "~~~\n## 判定\n| 判定 | No-Go |\n~~~~",
            "<!--\n## 判定\n| 判定 | No-Go |\n-->",
            "    ## 判定\n    | 判定 | No-Go |",
        ):
            with self.subTest(example=example):
                self.assertEqual(Command()._validate_record(self._record(example + "\n## 判定\n| 判定 | Go |")), [])

    def test_shorter_or_other_fence_does_not_close_a_code_sample(self):
        for section in (
            "````\n```\n## 判定\n| 判定 | Go |\n````",
            "```\n~~~\n## 判定\n| 判定 | Go |\n```",
            "```\n```not-a-closing-fence\n## 判定\n| 判定 | Go |\n```",
        ):
            with self.subTest(section=section):
                self.assertTrue(Command()._validate_record(self._record(section)))

    def test_go_does_not_replace_the_existing_evidence_requirements(self):
        self.assertTrue(Command()._validate_record("## 判定\n| 判定 | Go |"))

    def test_whitespace_and_crlf_in_an_actual_final_table_are_accepted(self):
        self.assertEqual(Command()._validate_record(self._record(" ## 判定\r\n  | 判定 |  Go  |  \r\n")), [])

    @override_settings(STRIPE_CHECKOUT_ENABLED=False)
    def test_disabled_checkout_behavior_is_unchanged(self):
        output = StringIO()
        call_command("billing_release_gate", stdout=output)
        self.assertIn("billing_release_gate=ok checkout-disabled", output.getvalue())
        with self.assertRaisesMessage(CommandError, "paid Checkout is required"):
            call_command("billing_release_gate", "--require-paid-checkout", stdout=StringIO())
