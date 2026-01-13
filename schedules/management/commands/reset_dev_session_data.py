"""
Reset and seed development users + session data for manual testing.

This command is intended for local development only (DEBUG=True).
It deletes known dev login users (admin/keeper/investigator/flow) and recreates
session-related sample data, including multiple SessionOccurrences.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection, transaction
from django.utils import timezone

from accounts.models import Group, GroupMembership
from schedules.models import SessionOccurrence, TRPGSession

User = get_user_model()


@dataclass(frozen=True)
class SeedUserSpec:
    username: str
    password: str
    email: str
    nickname: str
    is_staff: bool = False
    is_superuser: bool = False


def _table_exists(model) -> bool:
    return model._meta.db_table in connection.introspection.table_names()


def _make_local_datetime(now_local: datetime, *, days: int, hour: int, minute: int = 0) -> datetime:
    base = now_local + timedelta(days=days)
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


class Command(BaseCommand):
    help = '開発用ログインユーザーとセッションの手動テストデータをリセットして作成します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='確認プロンプトなしで削除/再作成します',
        )
        parser.add_argument(
            '--skip-flow',
            action='store_true',
            help='flow_* の導線テストデータ作成(create_flow_test_data)をスキップします',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('This command is only available in development (DEBUG=True).')

        if not _table_exists(SessionOccurrence):
            raise CommandError(
                'SessionOccurrence テーブルが見つかりません。先に `python manage.py migrate` を実行してください。'
            )

        force = bool(options.get('force'))
        skip_flow = bool(options.get('skip_flow'))

        seed_usernames = (
            ['admin', 'keeper1', 'keeper2']
            + [f'investigator{i}' for i in range(1, 7)]
            + ['flow_gm']
            + [f'flow_pl{i}' for i in range(1, 5)]
        )

        existing_users = list(User.objects.filter(username__in=seed_usernames).order_by('username'))
        if existing_users and not force:
            self.stdout.write(self.style.WARNING('以下の開発用ユーザーを削除して再作成します:'))
            for user in existing_users:
                self.stdout.write(f'- {user.username}')
            confirm = input('続行しますか？ (yes/no): ').strip().lower()
            if confirm != 'yes':
                self.stdout.write(self.style.WARNING('中止しました。'))
                return

        # Delete groups first so we do not leave orphaned Group.created_by references in DBs
        # where FK constraints/cascades are not enforced.
        Group.objects.filter(created_by__username__in=seed_usernames).delete()

        deleted_count, _ = User.objects.filter(username__in=seed_usernames).delete()
        self.stdout.write(self.style.SUCCESS(f'削除: {deleted_count} 件'))

        self._ensure_admin()

        # Recreate the baseline session dataset (keeper/investigator users, groups, sessions, etc).
        call_command('create_session_test_data', verbosity=options.get('verbosity', 1))

        if not skip_flow:
            call_command(
                'create_flow_test_data',
                verbosity=options.get('verbosity', 1),
            )

        self._add_occurrences_and_attendance()
        self._assert_foreign_keys_ok()

        self.stdout.write(self.style.SUCCESS('開発用セッション手動テストデータの準備が完了しました'))
        self.stdout.write('ログイン:')
        self.stdout.write('- /accounts/dev-login/ からユーザーを選択してログイン')
        self.stdout.write('- 管理者: admin / arkham_admin_2024')
        self.stdout.write('- GM: keeper1, keeper2 / keeper123')
        self.stdout.write('- PL: investigator1-6 / player123')

    def _assert_foreign_keys_ok(self) -> None:
        if connection.vendor != 'sqlite':
            return
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_key_check')
            rows = cursor.fetchall()
        if not rows:
            return

        self.stdout.write(self.style.ERROR('外部キー整合性エラーが検出されました (PRAGMA foreign_key_check):'))
        # PRAGMA foreign_key_check returns: (table, rowid, parent, fkid)
        with connection.cursor() as cursor:
            fk_list_cache: dict[str, list[tuple]] = {}

            for table, rowid, parent, fk_id in rows[:50]:
                if table not in fk_list_cache:
                    cursor.execute(f'PRAGMA foreign_key_list("{table}")')
                    fk_list_cache[table] = cursor.fetchall()

                fk_defs = [d for d in fk_list_cache[table] if d[0] == fk_id]
                from_cols = [d[3] for d in fk_defs] or ['<unknown>']

                if from_cols and from_cols[0] != '<unknown>':
                    cols_sql = ', '.join([f'"{col}"' for col in from_cols])
                    cursor.execute(f'SELECT {cols_sql} FROM "{table}" WHERE rowid = %s', [rowid])
                    values = cursor.fetchone()
                    self.stdout.write(f'- {table} rowid={rowid} -> {parent} fk_id={fk_id} {list(zip(from_cols, values or []))}')
                else:
                    self.stdout.write(f'- {table} rowid={rowid} -> {parent} fk_id={fk_id}')
        raise CommandError('Foreign key constraint failed (see output above).')

    def _ensure_admin(self) -> None:
        admin_spec = SeedUserSpec(
            username='admin',
            password='arkham_admin_2024',
            email='admin@arkham.nexus',
            nickname='アーカムの管理者',
            is_staff=True,
            is_superuser=True,
        )

        admin = User.objects.filter(username=admin_spec.username).first()
        if not admin:
            admin = User.objects.create_superuser(
                username=admin_spec.username,
                email=admin_spec.email,
                password=admin_spec.password,
                nickname=admin_spec.nickname,
            )
            self.stdout.write(self.style.SUCCESS('管理者ユーザー(admin)を作成しました'))
            return

        changed_fields: set[str] = set()
        if not admin.is_superuser:
            admin.is_superuser = True
            changed_fields.add('is_superuser')
        if not admin.is_staff:
            admin.is_staff = True
            changed_fields.add('is_staff')
        if admin.email != admin_spec.email:
            admin.email = admin_spec.email
            changed_fields.add('email')
        if getattr(admin, 'nickname', '') != admin_spec.nickname:
            admin.nickname = admin_spec.nickname
            changed_fields.add('nickname')
        if not admin.check_password(admin_spec.password):
            admin.set_password(admin_spec.password)
            changed_fields.add('password')

        if changed_fields:
            admin.save()
            self.stdout.write(self.style.SUCCESS('管理者ユーザー(admin)を更新しました'))

    def _add_occurrences_and_attendance(self) -> None:
        """
        Add extra occurrences to certain sessions and set per-occurrence participants/content.

        - Always sync primary occurrence participants = (GM + SessionParticipant users).
        - Add additional occurrences to planned/completed sessions to allow manual UI testing.
        """

        # Ensure group memberships exist (create_session_test_data should create them, but keep safe).
        for group in Group.objects.all():
            # Ensure creator is at least a member.
            try:
                created_by = group.created_by
            except User.DoesNotExist:
                continue
            if not GroupMembership.objects.filter(group=group, user=created_by).exists():
                GroupMembership.objects.create(user=created_by, group=group, role='admin')

        sessions = list(
            TRPGSession.objects.select_related('gm', 'group').prefetch_related('sessionparticipant_set__user')
        )

        # 1) Sync primary occurrences with baseline participants.
        for session in sessions:
            primary = session.occurrences.filter(is_primary=True).first()
            if not primary:
                continue
            participant_users = list(session.sessionparticipant_set.values_list('user', flat=True))
            user_ids = {session.gm_id, *participant_users}
            primary.participants.set(User.objects.filter(id__in=user_ids))

        tz = timezone.get_current_timezone()
        now_local = timezone.localtime(timezone.now(), tz)

        def add_occurrence(
            session: TRPGSession,
            *,
            start_at: datetime,
            participants: Iterable[str] | None,
            content: str,
        ) -> None:
            occurrence = SessionOccurrence.objects.create(
                session=session,
                start_at=start_at,
                content=content,
                is_primary=False,
            )
            if participants is None:
                return
            users = list(User.objects.filter(username__in=list(participants)))
            occurrence.participants.set(users)

        # 2) Add multi-date occurrences for specific sessions by title.
        def session_by_title(title: str) -> TRPGSession | None:
            return next((s for s in sessions if s.title == title), None)

        # Planned: add 2 extra dates, with one blank content and varying attendees.
        innsmouth = session_by_title('インスマスからの脱出')
        if innsmouth:
            add_occurrence(
                innsmouth,
                start_at=_make_local_datetime(now_local, days=10, hour=20),
                participants=['keeper1', 'investigator1', 'investigator2', 'investigator3'],
                content='第2回: 漁村の調査（内容は後で編集してOK）',
            )
            add_occurrence(
                innsmouth,
                start_at=_make_local_datetime(now_local, days=17, hour=20),
                participants=['keeper1', 'investigator1', 'investigator3'],
                content='',
            )

        # Completed: add a "後日談" date (content optional) to test history-style listing.
        miskatonic = session_by_title('ミスカトニック大学の怪異')
        if miskatonic:
            add_occurrence(
                miskatonic,
                start_at=_make_local_datetime(now_local, days=-6, hour=19, minute=30),
                participants=['keeper2', 'investigator3', 'investigator4', 'investigator5'],
                content='後日談: キャンパスでの聞き込み（メモ）',
            )

        # A dedicated manual session with multiple dates and per-date participant changes.
        group = Group.objects.filter(name='アーカムの探索者たち').first()
        gm = User.objects.filter(username='keeper1').first()
        if group and gm:
            multi = TRPGSession.objects.create(
                title='【MANUAL】複数日程テスト（参加者/内容）',
                description='日程ごとに参加者・内容を変える動作確認用',
                date=_make_local_datetime(now_local, days=2, hour=21),
                location='オンライン',
                gm=gm,
                group=group,
                status='planned',
                visibility='group',
                duration_minutes=240,
            )

            # Seed baseline session participants (legacy) for access checks.
            for slot, username in enumerate(['investigator1', 'investigator2', 'investigator3', 'investigator4'], start=1):
                user = User.objects.filter(username=username).first()
                if not user:
                    continue
                multi.sessionparticipant_set.create(user=user, role='player', player_slot=slot)

            # Primary occurrence attendance
            primary = multi.occurrences.filter(is_primary=True).first()
            if primary:
                primary.participants.set(User.objects.filter(username__in=['keeper1', 'investigator1', 'investigator2']))
                primary.content = '第1回: 導入（内容あり）'
                primary.save(update_fields=['content', 'updated_at'])

            # Additional occurrences
            add_occurrence(
                multi,
                start_at=_make_local_datetime(now_local, days=9, hour=21),
                participants=['keeper1', 'investigator2', 'investigator3'],
                content='',
            )
            add_occurrence(
                multi,
                start_at=_make_local_datetime(now_local, days=16, hour=21),
                participants=['keeper1', 'investigator1', 'investigator3', 'investigator4'],
                content='第3回: クライマックス',
            )
            add_occurrence(
                multi,
                start_at=_make_local_datetime(now_local, days=23, hour=21),
                participants=None,  # intentionally empty to test "未設定" state
                content='',
            )
