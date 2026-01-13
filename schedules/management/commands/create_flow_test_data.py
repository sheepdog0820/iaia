"""
シナリオ → セッション → 探索者（技能設定済み） の導線を確認するためのテストデータ作成コマンド

- シナリオ: 推奨技能あり
- セッション: シナリオと紐付け
- 探索者: 技能を設定し、シナリオ由来フィールドを設定
- ハンドアウト: HO1-HO4（秘匿）+ 共通（公開）
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Group
from accounts.character_models import CharacterSheet, CharacterSkill
from scenarios.models import Scenario
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo

User = get_user_model()


class Command(BaseCommand):
    help = 'シナリオ→セッション→探索者導線用のテストデータを作成します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='同名のフローテストデータを削除して作り直します',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        prefix = 'flow_'
        group_name = '【FLOWTEST】シナリオ起点グループ'
        scenario_title = '【FLOWTEST】推奨技能ありシナリオ'
        session_title = '【FLOWTEST】シナリオ起点セッション'

        usernames = [f'{prefix}gm'] + [f'{prefix}pl{i}' for i in range(1, 5)]
        if options.get('reset'):
            self._reset_data(
                group_name=group_name,
                scenario_title=scenario_title,
                session_title=session_title,
                usernames=usernames,
            )

        gm = self._get_or_create_user(
            username=f'{prefix}gm',
            nickname='フローテストGM',
            password='flowpass123',
            defaults={'is_staff': True},
        )
        players = [
            self._get_or_create_user(
                username=f'{prefix}pl{i}',
                nickname=f'フローテストPL{i}',
                password='flowpass123',
            )
            for i in range(1, 5)
        ]

        group = self._get_or_create_group(group_name, created_by=gm, members=[gm, *players])

        scenario = self._get_or_create_scenario(
            title=scenario_title,
            created_by=gm,
            author='フローテスト作者',
            summary='推奨技能/シナリオ→セッション→探索者導線の動作確認用シナリオ。',
            recommended_players='4人',
            recommended_skills='目星, 聞き耳, 図書館, オカルト, 交渉技能',
        )

        session = self._get_or_create_session(
            title=session_title,
            gm=gm,
            group=group,
            scenario=scenario,
            description='シナリオ起点テストデータ用セッション（導線確認）。',
            date=timezone.now().replace(hour=20, minute=0, second=0, microsecond=0) + timedelta(days=3),
            location='オンライン（Discord）',
        )

        # 探索者（技能設定済み）を作成し、セッション参加情報に紐付け
        recommended_skill_list = self._parse_recommended_skills(scenario.recommended_skills)
        for slot, user in enumerate(players, start=1):
            character = self._get_or_create_character(
                user=user,
                name=f'【FLOWTEST】探索者PL{slot}',
                occupation=['私立探偵', '医師', '大学教授', '古書店主'][slot - 1],
                age=[32, 28, 52, 40][slot - 1],
                source_scenario=scenario,
                recommended_skills=recommended_skill_list,
                skills=self._build_character_skills_for_slot(slot),
            )

            participant = SessionParticipant.objects.filter(session=session, user=user).first()
            if not participant:
                participant = SessionParticipant.objects.create(
                    session=session,
                    user=user,
                    role='player',
                    player_slot=slot,
                    character_name=character.name,
                    character_sheet=character,
                )
            else:
                changed = False
                if participant.player_slot != slot:
                    participant.player_slot = slot
                    changed = True
                if participant.character_sheet_id != character.id:
                    participant.character_sheet = character
                    changed = True
                if participant.character_name != character.name:
                    participant.character_name = character.name
                    changed = True
                if changed:
                    participant.save(update_fields=['player_slot', 'character_sheet', 'character_name'])

            # HO1-HO4（秘匿）
            self._get_or_create_handout(
                session=session,
                participant=participant,
                handout_number=slot,
                assigned_player_slot=slot,
                title=f'HO{slot}: 秘匿ハンドアウト',
                content=self._handout_content_for_slot(slot),
                recommended_skills=self._handout_recommended_skills_for_slot(slot),
                is_secret=True,
            )

        # 共通（公開）ハンドアウト：参加者は全員閲覧可（is_secret=False）
        any_participant = SessionParticipant.objects.filter(session=session, player_slot=1).first()
        if any_participant:
            self._get_or_create_handout(
                session=session,
                participant=any_participant,
                handout_number=None,
                assigned_player_slot=None,
                title='共通ハンドアウト（公開）: 導入',
                content='本シナリオは導線確認用です。参加者全員が閲覧できる公開ハンドアウトの動作を確認してください。',
                recommended_skills='',
                is_secret=False,
            )

        self.stdout.write(self.style.SUCCESS('フローテストデータを作成しました。'))
        self.stdout.write('ログイン情報:')
        self.stdout.write(f'- GM: {gm.username} / flowpass123')
        self.stdout.write(f'- PL: {players[0].username} / flowpass123 (他 {players[-1].username} まで)')
        self.stdout.write('作成データ:')
        self.stdout.write(f'- シナリオ: {scenario.title}')
        self.stdout.write(f'- セッション: {session.title}')

    def _reset_data(self, *, group_name, scenario_title, session_title, usernames):
        # セッション/参加情報/ハンドアウト
        target_sessions = TRPGSession.objects.filter(title=session_title)
        HandoutInfo.objects.filter(session__in=target_sessions).delete()
        SessionParticipant.objects.filter(session__in=target_sessions).delete()
        target_sessions.delete()

        # 探索者（ユーザー単位で削除するのは危険なので、名前プレフィックスで対象のみ）
        CharacterSkill.objects.filter(character_sheet__name__startswith='【FLOWTEST】').delete()
        CharacterSheet.objects.filter(name__startswith='【FLOWTEST】').delete()

        # シナリオ/グループ
        Scenario.objects.filter(title=scenario_title).delete()
        Group.objects.filter(name=group_name).delete()

        # ユーザー（自動生成分のみ）
        User.objects.filter(username__in=usernames).delete()

    def _get_or_create_user(self, *, username, nickname, password, defaults=None):
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
            if nickname and user.nickname != nickname:
                user.nickname = nickname
            user.save()
        return user

    def _get_or_create_group(self, name, *, created_by, members):
        group = Group.objects.filter(name=name).first()
        if not group:
            group = Group.objects.create(
                name=name,
                created_by=created_by,
                visibility='private',
                description='フローテストデータ用グループ',
            )
        group.members.add(*members)
        return group

    def _get_or_create_scenario(
        self,
        *,
        title,
        created_by,
        author,
        summary,
        recommended_players,
        recommended_skills,
    ):
        scenario = Scenario.objects.filter(title=title, created_by=created_by).first()
        if not scenario:
            scenario = Scenario.objects.create(
                title=title,
                author=author,
                game_system='coc',
                difficulty='beginner',
                estimated_duration='short',
                summary=summary,
                recommended_players=recommended_players,
                recommended_skills=recommended_skills,
                created_by=created_by,
            )
            return scenario

        changed = False
        if scenario.author != author:
            scenario.author = author
            changed = True
        if scenario.summary != summary:
            scenario.summary = summary
            changed = True
        if scenario.recommended_players != recommended_players:
            scenario.recommended_players = recommended_players
            changed = True
        if scenario.recommended_skills != recommended_skills:
            scenario.recommended_skills = recommended_skills
            changed = True
        if changed:
            scenario.save(update_fields=['author', 'summary', 'recommended_players', 'recommended_skills', 'updated_at'])
        return scenario

    def _get_or_create_session(self, *, title, gm, group, scenario, description, date, location):
        session = TRPGSession.objects.filter(title=title, gm=gm, group=group).first()
        if not session:
            return TRPGSession.objects.create(
                title=title,
                description=description,
                date=date,
                location=location,
                gm=gm,
                group=group,
                scenario=scenario,
                status='planned',
                visibility='private',
                duration_minutes=240,
            )

        changed = False
        if session.scenario_id != scenario.id:
            session.scenario = scenario
            changed = True
        if session.description != description:
            session.description = description
            changed = True
        if session.location != location:
            session.location = location
            changed = True
        if changed:
            session.save(update_fields=['scenario', 'description', 'location', 'updated_at'])
        return session

    def _get_or_create_character(
        self,
        *,
        user,
        name,
        occupation,
        age,
        source_scenario,
        recommended_skills,
        skills,
    ):
        character = CharacterSheet.objects.filter(user=user, name=name).first()
        if not character:
            character = CharacterSheet.objects.create(
                user=user,
                name=name,
                occupation=occupation,
                age=age,
                edition='6th',
                recommended_skills=list(recommended_skills or []),
                source_scenario=source_scenario,
                source_scenario_title=source_scenario.title if source_scenario else '',
                source_scenario_game_system=source_scenario.game_system if source_scenario else '',
                str_value=11,
                con_value=12,
                pow_value=13,
                dex_value=12,
                app_value=11,
                siz_value=12,
                int_value=14,
                edu_value=15,
                hit_points_max=12,
                hit_points_current=12,
                magic_points_max=13,
                magic_points_current=13,
                sanity_max=70,
                sanity_current=65,
                sanity_starting=65,
            )

        changed = False
        if source_scenario and character.source_scenario_id != source_scenario.id:
            character.source_scenario = source_scenario
            character.source_scenario_title = source_scenario.title
            character.source_scenario_game_system = source_scenario.game_system
            changed = True
        desired_recommended = list(recommended_skills or [])
        if desired_recommended and character.recommended_skills != desired_recommended:
            character.recommended_skills = desired_recommended
            changed = True
        if changed:
            character.save(update_fields=['source_scenario', 'source_scenario_title', 'source_scenario_game_system', 'recommended_skills', 'updated_at'])

        # skills は既存があっても上書きして揃える（導線確認用データのため）
        for skill_name, value in (skills or []):
            try:
                desired_total = int(value)
            except (TypeError, ValueError):
                continue

            base_value = character._get_skill_base_value(skill_name)
            if base_value is None:
                base_value = 0
            try:
                base_value = int(base_value)
            except (TypeError, ValueError):
                base_value = 0

            if desired_total < base_value:
                # ルール上の基本値より低い場合は「基本値をカスタム」として扱う
                base_value = desired_total
                occupation_points = 0
            else:
                occupation_points = desired_total - base_value

            skill = CharacterSkill.objects.filter(character_sheet=character, skill_name=skill_name).first()
            if not skill:
                skill = CharacterSkill(character_sheet=character, skill_name=skill_name)

            skill.category = character._get_skill_category(skill_name)
            skill.base_value = base_value
            skill.occupation_points = occupation_points
            skill.interest_points = 0
            skill.other_points = 0
            skill.save(skip_point_validation=True)
        return character

    def _get_or_create_handout(
        self,
        *,
        session,
        participant,
        handout_number,
        assigned_player_slot,
        title,
        content,
        recommended_skills,
        is_secret,
    ):
        qs = HandoutInfo.objects.filter(
            session=session,
            participant=participant,
            title=title,
        )
        if handout_number is not None:
            qs = qs.filter(handout_number=handout_number)

        handout = qs.first()
        if not handout:
            return HandoutInfo.objects.create(
                session=session,
                participant=participant,
                title=title,
                content=content,
                recommended_skills=recommended_skills,
                is_secret=is_secret,
                handout_number=handout_number,
                assigned_player_slot=assigned_player_slot,
            )

        changed = False
        if handout.content != content:
            handout.content = content
            changed = True
        if handout.recommended_skills != recommended_skills:
            handout.recommended_skills = recommended_skills
            changed = True
        if handout.is_secret != is_secret:
            handout.is_secret = is_secret
            changed = True
        if handout.assigned_player_slot != assigned_player_slot:
            handout.assigned_player_slot = assigned_player_slot
            changed = True
        if changed:
            handout.save(update_fields=['content', 'recommended_skills', 'is_secret', 'assigned_player_slot', 'updated_at'])
        return handout

    def _parse_recommended_skills(self, raw_value):
        if not raw_value:
            return []
        parts = [part.strip() for part in str(raw_value).replace('\n', ',').split(',')]
        return [part for part in parts if part]

    def _build_character_skills_for_slot(self, slot):
        skill_sets = {
            1: [
                ('目星', 70),
                ('聞き耳', 60),
                ('図書館', 55),
                ('心理学', 45),
                ('鍵開け', 40),
            ],
            2: [
                ('医学', 75),
                ('応急手当', 65),
                ('薬学', 55),
                ('聞き耳', 40),
                ('図書館', 40),
            ],
            3: [
                ('図書館', 85),
                ('歴史', 75),
                ('オカルト', 60),
                ('目星', 45),
                ('言語学', 50),
            ],
            4: [
                ('図書館', 70),
                ('オカルト', 70),
                ('目星', 55),
                ('心理学', 40),
                ('交渉技能', 45),
            ],
        }
        return skill_sets.get(slot, [('目星', 40), ('聞き耳', 40)])

    def _handout_content_for_slot(self, slot):
        contents = {
            1: 'あなたは最近、「霧の図書館」という噂を追っている。失踪者の足取りがそこへ向かっていた。',
            2: 'あなたは医療関係者として、原因不明の症状の相談を受けた。患者は奇妙な本の話をしていた。',
            3: 'あなたは研究対象の古文書に、図書館の地下に関する記述を見つけた。',
            4: 'あなたは古書店主として、出所不明の禁書の買い取り依頼を受けた。',
        }
        return contents.get(slot, 'あなたには秘匿の目的がある。')

    def _handout_recommended_skills_for_slot(self, slot):
        skills = {
            1: '目星, 聞き耳, 鍵開け',
            2: '医学, 応急手当, 薬学',
            3: '図書館, 歴史, オカルト',
            4: '図書館, オカルト, 交渉技能',
        }
        return skills.get(slot, '目星, 聞き耳')
