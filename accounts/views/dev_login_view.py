"""
開発用ログインビュー
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, get_user_model
from django.contrib import messages
from django.views import View
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from accounts.models import GroupMembership
from schedules.models import TRPGSession, SessionParticipant

User = get_user_model()


class DevLoginView(View):
    """開発環境用のクイックログインビュー"""
    
    def get(self, request):
        # 本番環境では使用不可
        if not settings.DEBUG:
            raise PermissionDenied("This feature is only available in development.")

        seed_usernames = ['admin', 'keeper1', 'keeper2'] + [f'investigator{i}' for i in range(1, 7)]
        seed_users_qs = User.objects.filter(username__in=seed_usernames)
        users_by_username = {user.username: user for user in seed_users_qs}
        seeded_users = [users_by_username[name] for name in seed_usernames if name in users_by_username]

        qa_users = list(User.objects.filter(username__startswith='qa_').order_by('username'))
        demo_users = list(User.objects.filter(username__startswith='demo_').order_by('username'))
        other_users = list(
            User.objects.exclude(username__in=seed_usernames)
            .exclude(username__startswith='qa_')
            .exclude(username__startswith='demo_')
            .order_by('username')[:50]
        )

        display_users = []
        seen_user_ids = set()
        for user in [*seeded_users, *qa_users, *demo_users, *other_users]:
            if user.id in seen_user_ids:
                continue
            display_users.append(user)
            seen_user_ids.add(user.id)

        user_ids = [user.id for user in display_users]

        gm_sessions_by_user_id = {}
        for session in TRPGSession.objects.filter(gm_id__in=user_ids).select_related('group').order_by('-date'):
            gm_sessions_by_user_id.setdefault(session.gm_id, []).append(session)

        participant_rows_by_user_id = {}
        participant_qs = (
            SessionParticipant.objects.filter(user_id__in=user_ids)
            .select_related('session', 'session__group', 'character_sheet')
            .order_by('-session__date')
        )
        for row in participant_qs:
            participant_rows_by_user_id.setdefault(row.user_id, []).append(row)

        memberships_by_user_id = {}
        membership_qs = GroupMembership.objects.filter(user_id__in=user_ids).select_related('group').order_by('group__name')
        for membership in membership_qs:
            memberships_by_user_id.setdefault(membership.user_id, []).append(membership)

        def password_hint_for(username: str) -> str:
            if username == 'admin':
                return 'arkham_admin_2024'
            if username.startswith('keeper'):
                return 'keeper123'
            if username.startswith('investigator'):
                return 'player123'
            return ''

        def to_user_card(user: User) -> dict:
            gm_sessions = gm_sessions_by_user_id.get(user.id, [])
            participant_rows = participant_rows_by_user_id.get(user.id, [])
            memberships = memberships_by_user_id.get(user.id, [])

            badges = []
            if user.is_superuser:
                badges.append({'label': 'ADMIN', 'class': 'bg-danger'})
            elif user.is_staff:
                badges.append({'label': 'STAFF', 'class': 'bg-dark'})
            if gm_sessions:
                badges.append({'label': 'GM', 'class': 'bg-warning text-dark'})
            if participant_rows:
                badges.append({'label': 'PL', 'class': 'bg-primary'})

            lines = []
            password_hint = password_hint_for(user.username)
            if password_hint:
                lines.append(f"PW: {password_hint}")

            if gm_sessions:
                gm_items = [f"{s.title}（{s.get_status_display()}）" for s in gm_sessions]
                lines.append("GM: " + ", ".join(gm_items))

            if participant_rows:
                pl_items = []
                for row in participant_rows:
                    session = row.session
                    slot = f"Slot{row.player_slot}" if row.player_slot else "Slot-"
                    character_name = ""
                    if row.character_sheet_id and getattr(row.character_sheet, 'name', ''):
                        character_name = row.character_sheet.name
                    elif row.character_name:
                        character_name = row.character_name
                    character_label = f" / {character_name}" if character_name else ""
                    pl_items.append(f"{session.title}（{session.get_status_display()}） {slot}{character_label}")
                lines.append("PL: " + ", ".join(pl_items))

            if memberships:
                group_items = [f"{m.group.name}({m.get_role_display()})" for m in memberships]
                lines.append("Groups: " + ", ".join(group_items))

            if not lines:
                lines.append("セッション/グループ未参加")

            return {
                'username': user.username,
                'nickname': user.nickname or user.username,
                'badges': badges,
                'description': "\n".join(lines),
            }

        categories = []
        assigned_ids = set()

        admin_cards = [to_user_card(u) for u in display_users if u.is_superuser]
        if admin_cards:
            categories.append({'category': '管理者', 'users': admin_cards})
            assigned_ids.update([u.id for u in display_users if u.is_superuser])

        gm_cards = []
        for user in display_users:
            if user.id in assigned_ids:
                continue
            if user.username.startswith('keeper') or gm_sessions_by_user_id.get(user.id):
                gm_cards.append(to_user_card(user))
                assigned_ids.add(user.id)
        if gm_cards:
            categories.append({'category': 'ゲームマスター', 'users': gm_cards})

        player_cards = []
        for user in display_users:
            if user.id in assigned_ids:
                continue
            if user.username.startswith('investigator') or participant_rows_by_user_id.get(user.id):
                player_cards.append(to_user_card(user))
                assigned_ids.add(user.id)
        if player_cards:
            categories.append({'category': 'プレイヤー', 'users': player_cards})

        qa_cards = []
        for user in qa_users:
            if user.id in assigned_ids:
                continue
            qa_cards.append(to_user_card(user))
            assigned_ids.add(user.id)
        if qa_cards:
            categories.append({'category': 'QA テストユーザー', 'users': qa_cards})

        demo_cards = []
        for user in demo_users:
            if user.id in assigned_ids:
                continue
            demo_cards.append(to_user_card(user))
            assigned_ids.add(user.id)
        if demo_cards:
            categories.append({'category': 'デモユーザー', 'users': demo_cards})

        other_cards = []
        for user in other_users:
            if user.id in assigned_ids:
                continue
            other_cards.append(to_user_card(user))
            assigned_ids.add(user.id)
        if other_cards:
            categories.append({'category': 'その他のユーザー', 'users': other_cards})
        
        context = {
            'test_users': categories,
            'current_user': request.user if request.user.is_authenticated else None
        }
        
        return render(request, 'accounts/dev_login.html', context)
    
    def post(self, request):
        # 本番環境では使用不可
        if not settings.DEBUG:
            raise PermissionDenied("This feature is only available in development.")
        
        username = request.POST.get('username')
        if not username:
            messages.error(request, 'ユーザー名が指定されていません。')
            return redirect('dev_login')
        
        try:
            user = User.objects.get(username=username)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'{user.nickname or user.username} としてログインしました。')
            
            # 適切なページにリダイレクト
            next_url = request.GET.get('next') or request.POST.get('next') or reverse('dashboard')
            return redirect(next_url)
            
        except User.DoesNotExist:
            messages.error(request, f'ユーザー {username} が見つかりません。')
            return redirect('dev_login')
