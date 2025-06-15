from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import CustomUser, Group, GroupMembership
from schedules.models import TRPGSession, SessionParticipant
from scenarios.models import Scenario, PlayHistory


class SimpleTindalosMetricsView(APIView):
    """シンプルなTindalos Metrics - テスト用"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        year = request.query_params.get('year')
        game_system = request.query_params.get('game_system')
        
        # フィルタ条件の構築
        session_filter = Q(participants=user) | Q(gm=user)
        if year:
            session_filter &= Q(date__year=year)
        
        # セッション統計
        sessions = TRPGSession.objects.filter(session_filter, status='completed').distinct()
        session_count = sessions.count()
        
        # GM/プレイヤーセッション数
        gm_sessions = sessions.filter(gm=user)
        gm_session_count = gm_sessions.count()
        player_session_count = session_count - gm_session_count
        
        # 総プレイ時間（分単位）
        total_play_time = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
        
        # シナリオ数
        play_history_filter = Q(user=user)
        if year:
            play_history_filter &= Q(played_date__year=year)
        if game_system:
            play_history_filter &= Q(scenario__game_system=game_system)
            
        scenario_count = PlayHistory.objects.filter(
            play_history_filter
        ).values('scenario').distinct().count()
        
        return Response({
            'session_count': session_count,
            'gm_session_count': gm_session_count,
            'player_session_count': player_session_count,
            'total_play_time': total_play_time,
            'scenario_count': scenario_count
        })


class TindalosMetricsView(APIView):
    """Tindalos Metrics - 統合統計ビュー"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        year = int(request.query_params.get('year', timezone.now().year))
        
        # 年間統計
        yearly_stats = self._get_yearly_stats(user, year)
        
        # 月別統計
        monthly_stats = self._get_monthly_stats(user, year)
        
        # ゲームシステム別統計
        system_stats = self._get_system_stats(user, year)
        
        # 役割別統計（GM/PL）
        role_stats = self._get_role_stats(user, year)
        
        # グループ活動統計
        group_stats = self._get_group_stats(user, year)
        
        # プレイ履歴
        recent_sessions = self._get_recent_sessions(user, limit=10)
        
        return Response({
            'user': {
                'id': user.id,
                'nickname': user.nickname or user.username,
                'trpg_start_year': self._get_trpg_start_year(user),
            },
            'year': year,
            'yearly_stats': yearly_stats,
            'monthly_stats': monthly_stats,
            'system_stats': system_stats,
            'role_stats': role_stats,
            'group_stats': group_stats,
            'recent_sessions': recent_sessions,
        })
    
    def _get_yearly_stats(self, user, year):
        """年間統計データ"""
        sessions = TRPGSession.objects.filter(
            participants=user,
            date__year=year,
            status='completed'
        )
        
        total_sessions = sessions.count()
        total_minutes = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
        total_hours = round(total_minutes / 60, 1)
        
        # GM/PL別セッション数
        gm_sessions = sessions.filter(gm=user).count()
        pl_sessions = total_sessions - gm_sessions
        
        # 平均セッション時間
        avg_minutes = sessions.aggregate(avg=Avg('duration_minutes'))['avg'] or 0
        avg_hours = round(avg_minutes / 60, 1)
        
        # 参加グループ数
        active_groups = Group.objects.filter(
            sessions__participants=user,
            sessions__date__year=year,
            sessions__status='completed'
        ).distinct().count()
        
        # プレイしたシナリオ数
        played_scenarios = PlayHistory.objects.filter(
            user=user,
            played_date__year=year
        ).values('scenario').distinct().count()
        
        # 高度な統計計算
        completion_rate = self._calculate_completion_rate(user, year)
        trpg_experience_years = self._calculate_trpg_experience(user)
        current_streak = self._calculate_current_streak(user)
        longest_streak = self._calculate_longest_streak(user, year)
        favorite_day_of_week = self._calculate_favorite_day_of_week(user, year)
        peak_playing_hour = self._calculate_peak_playing_hour(user, year)
        
        return {
            'total_sessions': total_sessions,
            'total_hours': total_hours,
            'total_minutes': total_minutes,
            'gm_sessions': gm_sessions,
            'pl_sessions': pl_sessions,
            'avg_session_hours': avg_hours,
            'active_groups': active_groups,
            'played_scenarios': played_scenarios,
            'sessions_per_month': round(total_sessions / 12, 1),
            'completion_rate': completion_rate,
            'trpg_experience_years': trpg_experience_years,
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'favorite_day_of_week': favorite_day_of_week,
            'peak_playing_hour': peak_playing_hour,
        }
    
    def _get_monthly_stats(self, user, year):
        """月別統計データ"""
        monthly_data = []
        
        for month in range(1, 13):
            sessions = TRPGSession.objects.filter(
                participants=user,
                date__year=year,
                date__month=month,
                status='completed'
            )
            
            session_count = sessions.count()
            total_minutes = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
            total_hours = round(total_minutes / 60, 1)
            
            gm_count = sessions.filter(gm=user).count()
            pl_count = session_count - gm_count
            
            monthly_data.append({
                'month': month,
                'session_count': session_count,
                'total_hours': total_hours,
                'gm_count': gm_count,
                'pl_count': pl_count,
            })
        
        return monthly_data
    
    def _get_system_stats(self, user, year):
        """ゲームシステム別統計"""
        # PlayHistoryから集計
        system_data = PlayHistory.objects.filter(
            user=user,
            played_date__year=year
        ).values('scenario__game_system').annotate(
            count=Count('id'),
            total_time=Sum('session__duration_minutes')
        ).order_by('-count')
        
        result = []
        for item in system_data:
            system = item['scenario__game_system']
            system_name = dict(Scenario.GAME_SYSTEM_CHOICES).get(system, system)
            total_hours = round((item['total_time'] or 0) / 60, 1)
            
            result.append({
                'system': system,
                'system_name': system_name,
                'session_count': item['count'],
                'total_hours': total_hours,
            })
        
        return result
    
    def _get_role_stats(self, user, year):
        """役割別統計（GM/PL）"""
        # GM統計
        gm_sessions = TRPGSession.objects.filter(
            gm=user,
            date__year=year,
            status='completed'
        )
        
        gm_count = gm_sessions.count()
        gm_minutes = gm_sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
        gm_hours = round(gm_minutes / 60, 1)
        
        # PL統計
        pl_sessions = TRPGSession.objects.filter(
            participants=user,
            date__year=year,
            status='completed'
        ).exclude(gm=user)
        
        pl_count = pl_sessions.count()
        pl_minutes = pl_sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
        pl_hours = round(pl_minutes / 60, 1)
        
        return {
            'gm': {
                'session_count': gm_count,
                'total_hours': gm_hours,
                'percentage': round((gm_count / (gm_count + pl_count) * 100) if (gm_count + pl_count) > 0 else 0, 1),
            },
            'pl': {
                'session_count': pl_count,
                'total_hours': pl_hours,
                'percentage': round((pl_count / (gm_count + pl_count) * 100) if (gm_count + pl_count) > 0 else 0, 1),
            }
        }
    
    def _get_group_stats(self, user, year):
        """グループ活動統計"""
        group_data = []
        
        user_groups = Group.objects.filter(members=user)
        
        for group in user_groups:
            sessions = TRPGSession.objects.filter(
                group=group,
                participants=user,
                date__year=year,
                status='completed'
            )
            
            session_count = sessions.count()
            total_minutes = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
            total_hours = round(total_minutes / 60, 1)
            
            if session_count > 0:  # アクティブなグループのみ
                group_data.append({
                    'group_id': group.id,
                    'group_name': group.name,
                    'session_count': session_count,
                    'total_hours': total_hours,
                })
        
        return sorted(group_data, key=lambda x: x['session_count'], reverse=True)
    
    def _get_recent_sessions(self, user, limit=10):
        """最近のセッション履歴"""
        sessions = TRPGSession.objects.filter(
            participants=user,
            status='completed'
        ).select_related('group', 'gm').order_by('-date')[:limit]
        
        result = []
        for session in sessions:
            # ユーザーの役割を取得
            participant = SessionParticipant.objects.filter(
                session=session, user=user
            ).first()
            
            result.append({
                'id': session.id,
                'title': session.title,
                'date': session.date.isoformat(),
                'duration_hours': round(session.duration_minutes / 60, 1) if session.duration_minutes else 0,
                'group_name': session.group.name if session.group else '',
                'gm_name': session.gm.nickname or session.gm.username,
                'role': participant.role if participant else 'player',
                'character_name': participant.character_name if participant else '',
            })
        
        return result
    
    def _get_trpg_start_year(self, user):
        """TRPG開始年を推定"""
        earliest_session = TRPGSession.objects.filter(
            participants=user
        ).order_by('date').first()
        
        if earliest_session:
            return earliest_session.date.year
        
        return user.date_joined.year
    
    def _calculate_completion_rate(self, user, year):
        """セッション完了率の計算"""
        total_planned = TRPGSession.objects.filter(
            participants=user,
            date__year=year
        ).count()
        
        completed = TRPGSession.objects.filter(
            participants=user,
            date__year=year,
            status='completed'
        ).count()
        
        if total_planned == 0:
            return 0.0
        
        return round((completed / total_planned) * 100, 1)
    
    def _calculate_trpg_experience(self, user):
        """TRPG経験年数の計算"""
        start_year = self._get_trpg_start_year(user)
        current_year = timezone.now().year
        return current_year - start_year + 1
    
    def _calculate_current_streak(self, user):
        """現在の連続プレイ週数"""
        from datetime import timedelta
        
        # 最近の8週間のセッション情報を取得
        eight_weeks_ago = timezone.now() - timedelta(weeks=8)
        sessions = TRPGSession.objects.filter(
            participants=user,
            date__gte=eight_weeks_ago,
            status='completed'
        ).order_by('-date')
        
        if not sessions:
            return 0
        
        # 週ごとにグループ化
        current_week = timezone.now().isocalendar()[1]
        streak = 0
        
        for week_offset in range(8):
            check_week = current_week - week_offset
            if check_week <= 0:
                check_week += 52  # 前年の週
            
            week_sessions = sessions.filter(
                date__week=check_week
            )
            
            if week_sessions.exists():
                streak += 1
            else:
                break
        
        return streak
    
    def _calculate_longest_streak(self, user, year):
        """年間最長連続プレイ週数"""
        sessions = TRPGSession.objects.filter(
            participants=user,
            date__year=year,
            status='completed'
        ).order_by('date')
        
        if not sessions:
            return 0
        
        # 週番号を取得してストリークを計算
        weeks_with_sessions = set()
        for session in sessions:
            week_num = session.date.isocalendar()[1]
            weeks_with_sessions.add(week_num)
        
        # 連続週数の最大値を計算
        sorted_weeks = sorted(weeks_with_sessions)
        max_streak = 1
        current_streak = 1
        
        for i in range(1, len(sorted_weeks)):
            if sorted_weeks[i] == sorted_weeks[i-1] + 1:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1
        
        return max_streak if sorted_weeks else 0
    
    def _calculate_favorite_day_of_week(self, user, year):
        """お気に入りの曜日を計算"""
        sessions = TRPGSession.objects.filter(
            participants=user,
            date__year=year,
            status='completed'
        )
        
        day_counts = {}
        day_names = {
            0: '月曜日', 1: '火曜日', 2: '水曜日', 3: '木曜日',
            4: '金曜日', 5: '土曜日', 6: '日曜日'
        }
        
        for session in sessions:
            day_of_week = session.date.weekday()
            day_counts[day_of_week] = day_counts.get(day_of_week, 0) + 1
        
        if not day_counts:
            return None
        
        favorite_day = max(day_counts, key=day_counts.get)
        return {
            'day': day_names[favorite_day],
            'count': day_counts[favorite_day],
            'percentage': round((day_counts[favorite_day] / sum(day_counts.values())) * 100, 1)
        }
    
    def _calculate_peak_playing_hour(self, user, year):
        """ピークプレイ時間帯を計算"""
        sessions = TRPGSession.objects.filter(
            participants=user,
            date__year=year,
            status='completed'
        )
        
        hour_counts = {}
        
        for session in sessions:
            hour = session.date.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        if not hour_counts:
            return None
        
        peak_hour = max(hour_counts, key=hour_counts.get)
        return {
            'hour': peak_hour,
            'hour_display': f"{peak_hour:02d}:00-{(peak_hour+1):02d}:00",
            'count': hour_counts[peak_hour],
            'percentage': round((hour_counts[peak_hour] / sum(hour_counts.values())) * 100, 1)
        }


class UserRankingView(APIView):
    """ユーザーランキング"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        year = int(request.query_params.get('year', timezone.now().year))
        ranking_type = request.query_params.get('type', 'hours')  # hours, sessions, gm
        
        if ranking_type == 'hours':
            ranking = self._get_hours_ranking(year)
        elif ranking_type == 'sessions':
            ranking = self._get_sessions_ranking(year)
        elif ranking_type == 'gm':
            ranking = self._get_gm_ranking(year)
        else:
            ranking = []
        
        # テスト用に修正された構造
        users_data = []
        for rank_data in ranking:
            user_info = {
                'user': {
                    'id': rank_data['user_id'],
                    'nickname': rank_data['nickname']
                },
                'total_play_time': rank_data.get('total_hours', 0) * 60,  # 分単位に変換
                'session_count': rank_data.get('session_count', 0),
                'gm_count': rank_data.get('gm_count', 0) if 'gm_count' in rank_data else rank_data.get('gm_sessions', 0)
            }
            users_data.append(user_info)
        
        # 現在のユーザーが含まれていない場合は追加
        if not any(u['user']['id'] == request.user.id for u in users_data):
            # 現在のユーザーの統計を取得
            user_sessions = TRPGSession.objects.filter(
                Q(participants=request.user) | Q(gm=request.user),
                date__year=year,
                status='completed'
            ).distinct()
            
            total_minutes = user_sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
            session_count = user_sessions.count()
            gm_count = user_sessions.filter(gm=request.user).count()
            
            users_data.append({
                'user': {
                    'id': request.user.id,
                    'nickname': request.user.nickname or request.user.username
                },
                'total_play_time': total_minutes,
                'session_count': session_count,
                'gm_count': gm_count
            })
        
        return Response({
            'year': year,
            'type': ranking_type,
            'ranking': ranking,
            'users': users_data
        })
    
    def _get_hours_ranking(self, year):
        """プレイ時間ランキング"""
        users = CustomUser.objects.filter(
            sessions__date__year=year,
            sessions__status='completed'
        ).annotate(
            total_minutes=Sum('sessions__duration_minutes'),
            session_count=Count('sessions', distinct=True)
        ).order_by('-total_minutes')[:20]
        
        ranking = []
        for i, user in enumerate(users, 1):
            total_hours = round((user.total_minutes or 0) / 60, 1)
            ranking.append({
                'rank': i,
                'user_id': user.id,
                'nickname': user.nickname or user.username,
                'total_hours': total_hours,
                'session_count': user.session_count,
            })
        
        return ranking
    
    def _get_sessions_ranking(self, year):
        """セッション数ランキング"""
        users = CustomUser.objects.filter(
            sessions__date__year=year,
            sessions__status='completed'
        ).annotate(
            session_count=Count('sessions', distinct=True),
            total_minutes=Sum('sessions__duration_minutes')
        ).order_by('-session_count')[:20]
        
        ranking = []
        for i, user in enumerate(users, 1):
            total_hours = round((user.total_minutes or 0) / 60, 1)
            ranking.append({
                'rank': i,
                'user_id': user.id,
                'nickname': user.nickname or user.username,
                'session_count': user.session_count,
                'total_hours': total_hours,
            })
        
        return ranking
    
    def _get_gm_ranking(self, year):
        """GMセッション数ランキング"""
        users = CustomUser.objects.filter(
            gm_sessions__date__year=year,
            gm_sessions__status='completed'
        ).annotate(
            gm_count=Count('gm_sessions', distinct=True),
            gm_minutes=Sum('gm_sessions__duration_minutes')
        ).order_by('-gm_count')[:20]
        
        ranking = []
        for i, user in enumerate(users, 1):
            gm_hours = round((user.gm_minutes or 0) / 60, 1)
            ranking.append({
                'rank': i,
                'user_id': user.id,
                'nickname': user.nickname or user.username,
                'gm_count': user.gm_count,
                'gm_hours': gm_hours,
            })
        
        return ranking


class GroupStatisticsView(APIView):
    """グループ統計"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        year = int(request.query_params.get('year', timezone.now().year))
        
        # ユーザーが参加しているグループの統計
        user_groups = Group.objects.filter(members=request.user)
        
        group_stats = []
        for group in user_groups:
            stats = self._get_group_stats(group, year)
            if stats['session_count'] > 0:  # アクティブなグループのみ
                group_stats.append(stats)
        
        # セッション数でソート
        group_stats.sort(key=lambda x: x['session_count'], reverse=True)
        
        # テスト用に修正された構造
        groups_data = []
        for stats in group_stats:
            group_info = {
                'group': {
                    'id': stats['group_id'],
                    'name': stats['group_name']
                },
                'member_count': stats['total_members'],
                'session_count': stats['session_count'],
                'total_play_time': stats.get('total_hours', 0) * 60  # 分単位に変換
            }
            groups_data.append(group_info)
        
        return Response({
            'year': year,
            'groups': groups_data
        })
    
    def _get_group_stats(self, group, year):
        """個別グループの統計"""
        sessions = TRPGSession.objects.filter(
            group=group,
            date__year=year,
            status='completed'
        )
        
        session_count = sessions.count()
        total_minutes = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
        total_hours = round(total_minutes / 60, 1)
        
        # アクティブメンバー数（その年にセッションに参加したメンバー）
        active_members = sessions.values('participants').distinct().count()
        
        # 最も活発なGM
        top_gm = sessions.values('gm__nickname', 'gm__username').annotate(
            gm_count=Count('id')
        ).order_by('-gm_count').first()
        
        return {
            'group_id': group.id,
            'group_name': group.name,
            'session_count': session_count,
            'total_hours': total_hours,
            'avg_session_hours': round(total_hours / session_count, 1) if session_count > 0 else 0,
            'active_members': active_members,
            'total_members': group.members.count(),
            'top_gm': (top_gm['gm__nickname'] or top_gm['gm__username']) if top_gm else None,
            'top_gm_sessions': top_gm['gm_count'] if top_gm else 0,
        }