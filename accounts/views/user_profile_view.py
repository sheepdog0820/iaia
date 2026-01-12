"""
グループメンバー向けのプロフィール参照ビュー
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from accounts.forms import ProfileEditForm
from accounts.models import GroupMembership
from schedules.models import TRPGSession

User = get_user_model()


@method_decorator(login_required, name='dispatch')
class UserProfileView(TemplateView):
    template_name = 'account/user_profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        profile_user = get_object_or_404(User, pk=kwargs.get('user_id'))
        viewer = self.request.user

        shared_group_ids = list(
            GroupMembership.objects.filter(user=viewer).values_list('group_id', flat=True)
        )
        shared_groups = list(
            GroupMembership.objects.filter(user=profile_user, group_id__in=shared_group_ids)
            .select_related('group')
        )

        if profile_user.id != viewer.id and not viewer.is_superuser and not shared_groups:
            raise PermissionDenied("このプロフィールを閲覧する権限がありません。")

        sheet = getattr(profile_user, 'trpg_introduction_sheet', None) or {}
        visibility = sheet.get('visibility', '') if isinstance(sheet, dict) else ''

        viewer_is_kp = TRPGSession.objects.filter(gm=viewer, participants=profile_user).exists()
        show_trpg_sheet = (
            profile_user.id == viewer.id
            or viewer.is_superuser
            or visibility in ['', 'public', 'participants']
            or (visibility == 'kp_only' and viewer_is_kp)
        )

        env_labels = dict(ProfileEditForm.TRPG_ENVIRONMENT_CHOICES)
        system_labels = dict(ProfileEditForm.TRPG_SYSTEM_CHOICES)
        structure_labels = dict(ProfileEditForm.SCENARIO_STRUCTURE_CHOICES)
        play_feel_labels = dict(ProfileEditForm.SCENARIO_PLAY_FEEL_CHOICES)
        volume_labels = dict(ProfileEditForm.SCENARIO_VOLUME_CHOICES)
        preference_labels = dict(ProfileEditForm.STORY_PREFERENCE_CHOICES)
        ending_labels = dict(ProfileEditForm.ENDING_PREFERENCE_CHOICES)
        loss_labels = dict(ProfileEditForm.LOSS_PREFERENCE_CHOICES)
        rp_style_labels = dict(ProfileEditForm.RP_STYLE_CHOICES)
        role_pref_labels = dict(ProfileEditForm.ROLE_PREFERENCE_CHOICES)
        ok_ng_labels = dict(ProfileEditForm.OK_NG_CHOICES)
        ok_conditional_ng_labels = dict(ProfileEditForm.OK_CONDITIONAL_NG_CHOICES)
        ng_expression_labels = dict(ProfileEditForm.NG_EXPRESSION_CHOICES)
        ng_play_labels = dict(ProfileEditForm.NG_PLAY_CHOICES)
        ng_share_labels = dict(ProfileEditForm.NG_SHARE_METHOD_CHOICES)
        tempo_labels = dict(ProfileEditForm.SESSION_TEMPO_CHOICES)
        direction_labels = dict(ProfileEditForm.DIRECTION_AMOUNT_CHOICES)
        kp_ruling_labels = dict(ProfileEditForm.KP_RULING_CHOICES)
        visibility_labels = dict(ProfileEditForm.PROFILE_VISIBILITY_CHOICES)

        def add_item(items, label, value):
            if value in (None, '', [], {}):
                return
            if isinstance(value, list):
                rendered = ', '.join([str(v) for v in value if v not in (None, '', [], {})])
                if not rendered:
                    return
                items.append({'label': label, 'value': rendered})
                return
            items.append({'label': label, 'value': str(value)})

        trpg_sheet_sections = []
        if show_trpg_sheet and isinstance(sheet, dict):
            basic = sheet.get('basic', {}) or {}
            systems = sheet.get('systems', {}) or {}
            scenario = sheet.get('scenario', {}) or {}
            character_play = sheet.get('character_play', {}) or {}
            conflict = sheet.get('conflict', {}) or {}
            ng = sheet.get('ng', {}) or {}
            session_pref = sheet.get('session', {}) or {}
            free = sheet.get('free', {}) or {}

            sections_raw = [
                ('基本情報', [
                    ('主なプレイ環境', [env_labels.get(v, v) for v in (basic.get('environment') or [])]),
                    ('使用ツール', basic.get('tools') or ''),
                ]),
                ('対応システム', [
                    ('プレイ経験システム', [system_labels.get(v, v) for v in (systems.get('played') or [])]),
                    ('得意・好きなシステム', [system_labels.get(v, v) for v in (systems.get('favorite') or [])]),
                    ('その他', systems.get('other') or ''),
                ]),
                ('シナリオ傾向', [
                    ('シナリオ構造', structure_labels.get(scenario.get('structure') or '', '')),
                    ('プレイ感', play_feel_labels.get(scenario.get('play_feel') or '', '')),
                    ('ボリューム', volume_labels.get(scenario.get('volume') or '', '')),
                    ('物語・展開の嗜好', [preference_labels.get(v, v) for v in (scenario.get('preferences') or [])]),
                    ('エンディング傾向', ending_labels.get(scenario.get('ending') or '', '')),
                    ('ロスト', loss_labels.get(scenario.get('loss') or '', '')),
                    ('ロスト備考', scenario.get('loss_note') or ''),
                ]),
                ('キャラクタープレイ傾向', [
                    ('ロールプレイスタイル', [rp_style_labels.get(v, v) for v in (character_play.get('rp_style') or [])]),
                    ('得意・好きな役割', [role_pref_labels.get(v, v) for v in (character_play.get('role_preference') or [])]),
                ]),
                ('PvP・対立要素', [
                    ('軽度の対立', ok_ng_labels.get(conflict.get('light') or '', '')),
                    ('PvP', ok_conditional_ng_labels.get(conflict.get('pvp') or '', '')),
                    ('裏切り・秘密', ok_conditional_ng_labels.get(conflict.get('betrayal') or '', '')),
                    ('条件・備考', conflict.get('note') or ''),
                ]),
                ('地雷・NG要素', [
                    ('表現面のNG', [ng_expression_labels.get(v, v) for v in (ng.get('expression') or [])]),
                    ('表現面のNG（その他）', ng.get('expression_other') or ''),
                    ('プレイ面のNG', [ng_play_labels.get(v, v) for v in (ng.get('play') or [])]),
                    ('プレイ面のNG（その他）', ng.get('play_other') or ''),
                    ('事前共有方法', ng_share_labels.get(ng.get('share_method') or '', '')),
                ]),
                ('セッション進行の希望', [
                    ('セッションテンポ', tempo_labels.get(session_pref.get('tempo') or '', '')),
                    ('演出量', direction_labels.get(session_pref.get('direction_amount') or '', '')),
                    ('KP裁定へのスタンス', kp_ruling_labels.get(session_pref.get('kp_ruling') or '', '')),
                ]),
                ('フリーコメント', [
                    ('フリーコメント', free.get('comment') or ''),
                    ('公開範囲', visibility_labels.get(visibility or '', '')),
                ]),
            ]

            for title, raw_items in sections_raw:
                items = []
                for label, value in raw_items:
                    add_item(items, label, value)
                if items:
                    trpg_sheet_sections.append({'title': title, 'items': items})

        context.update({
            'profile_user': profile_user,
            'shared_groups': shared_groups,
            'show_trpg_sheet': show_trpg_sheet,
            'trpg_sheet_sections': trpg_sheet_sections,
        })
        return context
