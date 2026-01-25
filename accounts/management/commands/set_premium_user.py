from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


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

    def handle(self, *args, **options):
        identifier = options["identifier"]
        enable = True if options["on"] or not options["off"] else False

        User = get_user_model()
        user = (
            User.objects.filter(username=identifier).first()
            or User.objects.filter(email=identifier).first()
        )
        if user is None:
            raise CommandError(f"User not found: {identifier}")

        if not hasattr(user, "is_premium"):
            raise CommandError("This project does not have is_premium on the user model.")

        user.is_premium = enable
        user.save(update_fields=["is_premium"])

        state = "ON" if enable else "OFF"
        self.stdout.write(self.style.SUCCESS(f"is_premium={state} for user={user.username}"))

