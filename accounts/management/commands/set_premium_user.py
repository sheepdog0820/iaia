from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.billing import create_premium_audit_log, locked_manual_premium_user
from accounts.models import PremiumSubscription


class Command(BaseCommand):
    help = "ユーザーを課金ユーザ（高権限ユーザ）として設定/解除します。"

    def add_arguments(self, parser):
        parser.add_argument(
            "identifier",
            help="対象ユーザー（username または email）",
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--on",
            action="store_true",
            help="課金ユーザに設定",
        )
        group.add_argument(
            "--off",
            action="store_true",
            help="課金ユーザを解除",
        )

        parser.add_argument(
            "--reason",
            default="Manual premium access update by set_premium_user",
            help="監査ログに残す手動付与・解除理由です。",
        )

    def handle(self, *args, **options):
        identifier = options["identifier"]
        enable = True if options["on"] or not options["off"] else False
        reason = options["reason"]

        User = get_user_model()
        user = User.objects.filter(username=identifier).first() or User.objects.filter(email=identifier).first()
        if user is None:
            raise CommandError(f"User not found: {identifier}")

        if not hasattr(user, "is_premium"):
            raise CommandError("This project does not have is_premium on the user model.")

        try:
            with locked_manual_premium_user(user) as current:
                previous = current.is_premium
                current.is_premium = enable
                current.save(update_fields=["is_premium"])
                if previous != enable:
                    create_premium_audit_log(
                        current,
                        action="granted" if enable else "revoked",
                        source="manual",
                        reason=reason,
                        metadata={"command": "set_premium_user"},
                    )
        except User.DoesNotExist as exc:
            raise CommandError("対象ユーザーは削除されています。") from exc
        except PremiumSubscription.DoesNotExist as exc:
            raise CommandError("課金情報が変更されています。再試行してください。") from exc

        state = "ON" if enable else "OFF"
        self.stdout.write(self.style.SUCCESS(f"is_premium={state} for user={current.username}"))
