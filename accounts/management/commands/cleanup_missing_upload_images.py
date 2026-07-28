from dataclasses import dataclass

from django.core.management.base import BaseCommand

from accounts.character_models import (
    CharacterImage6th,
    CharacterImage7th,
    CharacterSheet6th,
    CharacterSheet7th,
)
from scenarios.models import ScenarioImage
from schedules.models import SessionImage


@dataclass(frozen=True)
class ImageTarget:
    model: type
    field_name: str
    delete_record: bool


IMAGE_TARGETS = (
    ImageTarget(ScenarioImage, "image", True),
    ImageTarget(SessionImage, "image", True),
    ImageTarget(CharacterImage6th, "image", True),
    ImageTarget(CharacterImage7th, "image", True),
    ImageTarget(CharacterSheet6th, "character_image", False),
    ImageTarget(CharacterSheet7th, "character_image", False),
)


class Command(BaseCommand):
    help = (
        "ストレージ上のファイルが存在しないシナリオ・セッション・"
        "キャラクター画像レコードを検出し、必要に応じて削除します。"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="リンク切れ画像レコードを削除します。省略時は確認のみです。",
        )

    def handle(self, *args, **options):
        should_delete = options["delete"]
        missing_count = 0
        deleted_count = 0
        error_count = 0

        if not should_delete:
            self.stdout.write("DRY RUN: データは変更しません。削除する場合は --delete を指定してください。")

        for target in IMAGE_TARGETS:
            queryset = target.model.objects.exclude(**{target.field_name: ""})
            for instance in queryset.iterator():
                field_file = getattr(instance, target.field_name)
                if not field_file or not getattr(field_file, "name", ""):
                    continue

                try:
                    exists = field_file.storage.exists(field_file.name)
                except Exception as exc:
                    error_count += 1
                    self.stderr.write(
                        f"確認失敗: {target.model.__name__} pk={instance.pk} " f"name={field_file.name} ({exc})"
                    )
                    continue

                if exists:
                    continue

                missing_count += 1
                self.stdout.write(f"リンク切れ: {target.model.__name__} pk={instance.pk} name={field_file.name}")
                if not should_delete:
                    continue

                if target.delete_record:
                    instance.delete()
                else:
                    type(instance).objects.filter(pk=instance.pk).update(**{target.field_name: ""})
                deleted_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"検出: {missing_count}件 / 削除: {deleted_count}件 / 確認エラー: {error_count}件")
        )
