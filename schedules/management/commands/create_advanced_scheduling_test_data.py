"""
ISSUE-017 (高度なスケジューリング) の手動テスト用データを作成します。

作成する主なデータ:
- グループ: 【ADVTEST】高度なスケジューリング
- セッションシリーズ（weekly/biweekly/monthly/custom）
- 日程調整（DatePoll）: オープン/確定済み
- 参加可能日投票（SessionAvailability）: session/occurrence それぞれ
"""

from __future__ import annotations

import calendar
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Group, GroupMembership
from scenarios.models import Scenario
from schedules.models import (
    DatePoll,
    DatePollOption,
    DatePollVote,
    SessionAvailability,
    SessionOccurrence,
    SessionSeries,
    TRPGSession,
)

try:
    from rest_framework.authtoken.models import Token
except Exception:  # pragma: no cover
    Token = None

User = get_user_model()


def _make_local_dt(*, days: int, hour: int, minute: int = 0):
    tz = timezone.get_current_timezone()
    now_local = timezone.localtime(timezone.now(), tz)
    dt = now_local + timedelta(days=days)
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0)


class Command(BaseCommand):
    help = 'ISSUE-017(高度なスケジューリング)の手動テストデータを作成します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='ADVTESTデータ（グループ/シナリオ/投票など）を削除して作り直します',
        )
        parser.add_argument(
            '--group-name',
            default='【ADVTEST】高度なスケジューリング',
            help='作成するグループ名',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        group_name = options.get('group_name')
        if options.get('reset'):
            self._reset(group_name)

        gm, players, created_users = self._resolve_users()
        group = self._get_or_create_group(group_name, gm, players)
        scenario = self._get_or_create_scenario(gm)

        series_weekly, seeded_sessions = self._seed_series(group, gm, scenario)
        self._seed_date_polls(group, gm, players)
        self._seed_availability(series_weekly, seeded_sessions, players)

        token_info = self._ensure_tokens([gm, *players])

        self.stdout.write(self.style.SUCCESS('高度なスケジューリング(ISSUE-017)のテストデータを作成しました。'))
        self.stdout.write('ログイン:')
        if created_users:
            self.stdout.write('- adv_gm / advpass123')
            self.stdout.write('- adv_pl1-3 / advpass123')
        else:
            self.stdout.write('- keeper1 / keeper123 (存在する場合)')
            self.stdout.write('- investigator1-3 / player123 (存在する場合)')
        self.stdout.write(f'グループ: {group.name}')
        self.stdout.write('API(例):')
        self.stdout.write('- /api/schedules/session-series/')
        self.stdout.write(f'- /api/schedules/session-series/{series_weekly.id}/generate_sessions/')
        self.stdout.write('- /api/schedules/availability/vote/')
        self.stdout.write('- /api/schedules/date-polls/')
        if token_info:
            self.stdout.write('TokenAuthentication:')
            for username, key in token_info.items():
                self.stdout.write(f'- {username}: {key}')

    def _reset(self, group_name: str) -> None:
        Group.objects.filter(name=group_name).delete()
        Scenario.objects.filter(title__startswith='【ADVTEST】').delete()
        User.objects.filter(username__in=['adv_gm', 'adv_pl1', 'adv_pl2', 'adv_pl3']).delete()

    def _resolve_users(self):
        gm = User.objects.filter(username='keeper1').first()
        players = [
            User.objects.filter(username='investigator1').first(),
            User.objects.filter(username='investigator2').first(),
            User.objects.filter(username='investigator3').first(),
        ]
        players = [p for p in players if p]

        created_users = False
        if not gm:
            created_users = True
            gm = self._get_or_create_user(
                username='adv_gm',
                nickname='ADVTEST GM',
                password='advpass123',
                defaults={'is_staff': True},
            )
        if len(players) < 3:
            created_users = True
            players = [
                self._get_or_create_user(
                    username=f'adv_pl{i}',
                    nickname=f'ADVTEST PL{i}',
                    password='advpass123',
                )
                for i in range(1, 4)
            ]

        return gm, players, created_users

    def _get_or_create_user(self, *, username: str, nickname: str, password: str, defaults=None):
        defaults = defaults or {}
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'nickname': nickname,
                **defaults,
            },
        )
        if created or not user.check_password(password):
            user.set_password(password)
            if nickname and getattr(user, 'nickname', '') != nickname:
                user.nickname = nickname
            user.save()
        return user

    def _get_or_create_group(self, name: str, gm, players):
        group = Group.objects.filter(name=name).first()
        if not group:
            group = Group.objects.create(
                name=name,
                created_by=gm,
                visibility='private',
                description='ISSUE-017(高度なスケジューリング)の手動テスト用グループ',
            )

        GroupMembership.objects.update_or_create(
            user=gm,
            group=group,
            defaults={'role': 'admin'},
        )
        for player in players:
            GroupMembership.objects.get_or_create(
                user=player,
                group=group,
                defaults={'role': 'member'},
            )

        return group

    def _get_or_create_scenario(self, gm):
        title = '【ADVTEST】定期セッション用シナリオ'
        scenario, created = Scenario.objects.get_or_create(
            title=title,
            created_by=gm,
            defaults={
                'author': 'ADVTEST',
                'game_system': 'coc',
                'difficulty': 'beginner',
                'estimated_duration': 'short',
                'summary': 'ISSUE-017(高度なスケジューリング)の手動テスト用シナリオ。',
                'recommended_players': '3人',
                'recommended_skills': '目星, 聞き耳, 図書館',
            },
        )
        if created:
            return scenario

        changed = False
        if scenario.summary != 'ISSUE-017(高度なスケジューリング)の手動テスト用シナリオ。':
            scenario.summary = 'ISSUE-017(高度なスケジューリング)の手動テスト用シナリオ。'
            changed = True
        if changed:
            scenario.save(update_fields=['summary', 'updated_at'])
        return scenario

    def _upsert_series(self, *, group, gm, scenario, title: str, defaults: dict):
        series = SessionSeries.objects.filter(title=title, group=group).first()
        if not series:
            return SessionSeries.objects.create(
                title=title,
                group=group,
                gm=gm,
                scenario=scenario,
                **defaults,
            )

        changed = False
        for field, value in defaults.items():
            if getattr(series, field) != value:
                setattr(series, field, value)
                changed = True
        if series.gm_id != gm.id:
            series.gm = gm
            changed = True
        if series.group_id != group.id:
            series.group = group
            changed = True
        if series.scenario_id != scenario.id:
            series.scenario = scenario
            changed = True
        if changed:
            series.save()
        return series

    def _seed_series(self, group, gm, scenario):
        today = timezone.localdate()
        first_day = today.replace(day=1)

        weekday_soon = (today.weekday() + 1) % 7
        weekday_next = (today.weekday() + 2) % 7

        series_weekly = self._upsert_series(
            group=group,
            gm=gm,
            scenario=scenario,
            title='【ADVTEST】毎週シリーズ',
            defaults={
                'recurrence': 'weekly',
                'weekday': weekday_soon,
                'start_date': today,
                'start_time': timezone.localtime(timezone.now()).replace(hour=20, minute=0).time(),
                'duration_minutes': 180,
                'auto_create_sessions': True,
                'auto_create_weeks_ahead': 4,
                'is_active': True,
            },
        )
        self._upsert_series(
            group=group,
            gm=gm,
            scenario=scenario,
            title='【ADVTEST】隔週シリーズ',
            defaults={
                'recurrence': 'biweekly',
                'weekday': weekday_next,
                'start_date': today,
                'start_time': timezone.localtime(timezone.now()).replace(hour=21, minute=0).time(),
                'duration_minutes': 210,
                'auto_create_sessions': True,
                'auto_create_weeks_ahead': 8,
                'is_active': True,
            },
        )

        last_day = calendar.monthrange(today.year, today.month)[1]
        day_of_month_soon = min(today.day + 1, last_day)
        self._upsert_series(
            group=group,
            gm=gm,
            scenario=scenario,
            title='【ADVTEST】毎月シリーズ(近日)',
            defaults={
                'recurrence': 'monthly',
                'day_of_month': day_of_month_soon,
                'start_date': first_day,
                'start_time': timezone.localtime(timezone.now()).replace(hour=19, minute=30).time(),
                'duration_minutes': 240,
                'auto_create_sessions': True,
                'auto_create_weeks_ahead': 12,
                'is_active': True,
            },
        )
        self._upsert_series(
            group=group,
            gm=gm,
            scenario=scenario,
            title='【ADVTEST】毎月シリーズ(月末)',
            defaults={
                'recurrence': 'monthly',
                'day_of_month': 31,
                'start_date': first_day,
                'start_time': timezone.localtime(timezone.now()).replace(hour=19, minute=0).time(),
                'duration_minutes': 180,
                'auto_create_sessions': True,
                'auto_create_weeks_ahead': 12,
                'is_active': True,
            },
        )
        self._upsert_series(
            group=group,
            gm=gm,
            scenario=scenario,
            title='【ADVTEST】カスタム(10日間隔)',
            defaults={
                'recurrence': 'custom',
                'custom_interval_days': 10,
                'start_date': today - timedelta(days=20),
                'start_time': timezone.localtime(timezone.now()).replace(hour=20, minute=0).time(),
                'duration_minutes': 180,
                'auto_create_sessions': False,
                'auto_create_weeks_ahead': 0,
                'is_active': True,
            },
        )

        seeded_sessions: list[TRPGSession] = []
        for d in series_weekly.get_next_session_dates(count=2):
            existing = series_weekly.sessions.filter(date__date=d).first()
            if existing:
                seeded_sessions.append(existing)
                continue
            seeded_sessions.append(series_weekly.create_session_for_date(d))

        return series_weekly, seeded_sessions

    def _seed_date_polls(self, group, gm, players):
        def create_poll(title: str, *, confirm: bool):
            DatePoll.objects.filter(title=title, group=group).delete()
            poll = DatePoll.objects.create(
                title=title,
                description='日程調整(ISSUE-017)の手動テスト用',
                group=group,
                created_by=gm,
                deadline=_make_local_dt(days=3, hour=23, minute=59),
                create_session_on_confirm=True,
            )

            option_datetimes = [
                _make_local_dt(days=2, hour=20),
                _make_local_dt(days=3, hour=20),
                _make_local_dt(days=4, hour=20),
            ]
            options = [
                DatePollOption.objects.create(poll=poll, datetime=dt, note=f'候補{i + 1}')
                for i, dt in enumerate(option_datetimes)
            ]

            # Votes
            statuses = ['available', 'maybe', 'unavailable']
            for user_index, user in enumerate([gm, *players]):
                for option_index, option in enumerate(options):
                    DatePollVote.objects.update_or_create(
                        option=option,
                        user=user,
                        defaults={
                            'status': statuses[(user_index + option_index) % 3],
                            'comment': '',
                        },
                    )

            if confirm:
                poll.confirm_date(options[0])

        create_poll('【ADVTEST】日程調整(オープン)', confirm=False)
        create_poll('【ADVTEST】日程調整(確定済み)', confirm=True)

    def _seed_availability(self, series_weekly, seeded_sessions, players):
        if not seeded_sessions:
            return

        session = seeded_sessions[0]
        for idx, player in enumerate(players, start=1):
            SessionAvailability.objects.update_or_create(
                session=session,
                user=player,
                defaults={
                    'status': ['available', 'maybe', 'unavailable'][idx % 3],
                    'comment': '手動テスト用',
                },
            )

        # occurrence vote: create an extra occurrence date and cast one vote.
        occurrence = session.occurrences.filter(is_primary=False).order_by('start_at').first()
        if not occurrence:
            occurrence = SessionOccurrence.objects.create(
                session=session,
                start_at=session.date + timedelta(days=1),
                content='追加日程(オカレンス)の手動テスト用',
                is_primary=False,
            )
        SessionAvailability.objects.update_or_create(
            occurrence=occurrence,
            user=players[0],
            defaults={
                'status': 'available',
                'comment': 'オカレンス投票',
            },
        )

    def _ensure_tokens(self, users):
        if Token is None:
            return {}

        token_map: dict[str, str] = {}
        for user in users:
            token, _ = Token.objects.get_or_create(user=user)
            token_map[user.username] = token.key
        return token_map

