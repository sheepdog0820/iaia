import csv
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import PremiumAccessCode


class Command(BaseCommand):
    help = '運営発行のプレミアムコードを作成します。コード本体はこの実行時にのみ表示されます。'

    def add_arguments(self, parser):
        parser.add_argument('--code', help='任意のコード文字列。未指定なら自動生成します。')
        parser.add_argument('--label', default='', help='管理用ラベル。複数発行時は末尾に連番を付けます。')
        parser.add_argument('--campaign', default='', help='キャンペーン名')
        parser.add_argument('--note', default='', help='管理用メモ')
        parser.add_argument('--max-uses', type=int, default=1, help='各コードの最大使用回数')
        parser.add_argument('--expires-in-days', type=int, help='有効期限（日数）')
        parser.add_argument('--created-by', help='作成者ユーザー名またはメールアドレス')
        parser.add_argument('--count', type=int, default=1, help='発行するコード数')
        parser.add_argument('--output-csv', help='発行したコードをCSVへ出力するパス')

    def handle(self, *args, **options):
        max_uses = options['max_uses']
        if max_uses < 1:
            raise CommandError('--max-uses must be greater than or equal to 1')

        count = options['count']
        if count < 1:
            raise CommandError('--count must be greater than or equal to 1')
        if options.get('code') and count != 1:
            raise CommandError('--code can only be used when --count is 1')

        expires_at = None
        if options.get('expires_in_days') is not None:
            if options['expires_in_days'] < 1:
                raise CommandError('--expires-in-days must be greater than or equal to 1')
            expires_at = timezone.now() + timedelta(days=options['expires_in_days'])

        created_by = None
        if options.get('created_by'):
            identifier = options['created_by']
            User = get_user_model()
            created_by = (
                User.objects.filter(username=identifier).first()
                or User.objects.filter(email=identifier).first()
            )
            if created_by is None:
                raise CommandError(f'User not found: {identifier}')

        issued = []
        for index in range(count):
            label = options.get('label') or ''
            if count > 1 and label:
                label = f'{label}-{index + 1}'
            try:
                access_code, raw_code = PremiumAccessCode.issue(
                    code=options.get('code'),
                    max_uses=max_uses,
                    expires_at=expires_at,
                    label=label,
                    campaign_name=options.get('campaign') or '',
                    note=options.get('note') or '',
                    created_by=created_by,
                )
            except Exception as exc:
                raise CommandError(f'Failed to issue premium code: {exc}') from exc
            issued.append((access_code, raw_code))

        if options.get('output_csv'):
            with open(options['output_csv'], 'w', newline='', encoding='utf-8') as handle:
                writer = csv.writer(handle)
                writer.writerow([
                    'id',
                    'code',
                    'label',
                    'campaign_name',
                    'status',
                    'max_uses',
                    'use_count',
                    'remaining_uses',
                    'expires_at',
                ])
                for access_code, raw_code in issued:
                    writer.writerow([
                        access_code.id,
                        raw_code,
                        access_code.label,
                        access_code.campaign_name,
                        access_code.status_label,
                        access_code.max_uses,
                        access_code.use_count,
                        max(access_code.max_uses - access_code.use_count, 0),
                        access_code.expires_at.isoformat() if access_code.expires_at else '',
                    ])

        self.stdout.write(self.style.SUCCESS(f'Premium code issued: {len(issued)}'))
        for access_code, raw_code in issued:
            self.stdout.write(f'id={access_code.id}')
            self.stdout.write(f'code={raw_code}')
            self.stdout.write(f'label={access_code.label}')
            self.stdout.write(f'campaign_name={access_code.campaign_name}')
            self.stdout.write(f'max_uses={access_code.max_uses}')
            self.stdout.write(f'expires_at={access_code.expires_at or ""}')
