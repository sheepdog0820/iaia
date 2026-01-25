from .views.common_imports import *
from .utils.statistics import SessionStatistics, CharacterStatistics, GroupStatistics, TindalosMetrics
from schedules.models import TRPGSession, SessionParticipant
from scenarios.models import Scenario, PlayHistory
from datetime import datetime, timedelta
from calendar import monthrange
from django.utils.dateparse import parse_date, parse_datetime
from django.db.models.functions import TruncMonth, TruncYear
from django.db.models import Max, Min


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
        
        # 年度・月別詳細集計を追加
        if request.query_params.get('detailed', 'false').lower() == 'true':
            yearly_trends = self._get_yearly_trends(user)
            monthly_details = self._get_monthly_details(user, year) if year else []
            popular_scenarios = self._get_popular_scenarios(user, year)
            system_trends = self._get_system_trends(user)
            
            return Response({
                'session_count': session_count,
                'gm_session_count': gm_session_count,
                'player_session_count': player_session_count,
                'total_play_time': total_play_time,
                'scenario_count': scenario_count,
                'yearly_trends': yearly_trends,
                'monthly_details': monthly_details,
                'popular_scenarios': popular_scenarios,
                'system_trends': system_trends
            })
        
        return Response({
            'session_count': session_count,
            'gm_session_count': gm_session_count,
            'player_session_count': player_session_count,
            'total_play_time': total_play_time,
            'scenario_count': scenario_count
        })
    
    def _get_yearly_trends(self, user):
        """複数年度にわたる統計データ"""
        # 最初のセッションから現在までの年度を取得
        first_session = TRPGSession.objects.filter(
            Q(participants=user) | Q(gm=user)
        ).order_by('date').first()
        
        if not first_session:
            return []
        
        start_year = first_session.date.year
        end_year = timezone.now().year
        
        yearly_data = []
        for year in range(start_year, end_year + 1):
            session_filter = (Q(participants=user) | Q(gm=user)) & Q(date__year=year)
            sessions = TRPGSession.objects.filter(session_filter, status='completed').distinct()
            
            session_count = sessions.count()
            gm_count = sessions.filter(gm=user).count()
            total_minutes = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
            
            yearly_data.append({
                'year': year,
                'session_count': session_count,
                'gm_session_count': gm_count,
                'player_session_count': session_count - gm_count,
                'total_hours': round(total_minutes / 60, 1),
                'avg_session_hours': round((total_minutes / session_count / 60), 1) if session_count > 0 else 0
            })
        
        return yearly_data
    
    def _get_monthly_details(self, user, year):
        """月別詳細統計（シナリオ別内訳含む）"""
        monthly_data = []
        
        for month in range(1, 13):
            # 月別セッション統計
            session_filter = (Q(participants=user) | Q(gm=user)) & Q(date__year=year) & Q(date__month=month)
            sessions = TRPGSession.objects.filter(session_filter, status='completed').distinct()
            
            session_count = sessions.count()
            total_minutes = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
            
            # 月別シナリオランキング（上位5件）
            scenarios = PlayHistory.objects.filter(
                user=user,
                played_date__year=year,
                played_date__month=month
            ).values(
                'scenario__id',
                'scenario__title',
                'scenario__game_system'
            ).annotate(
                play_count=Count('id')
            ).order_by('-play_count')[:5]
            
            monthly_data.append({
                'month': month,
                'session_count': session_count,
                'total_hours': round(total_minutes / 60, 1),
                'scenarios': list(scenarios)
            })
        
        return monthly_data
    
    def _get_popular_scenarios(self, user, year=None):
        """期間内の人気シナリオランキング"""
        filters = Q(user=user)
        if year:
            filters &= Q(played_date__year=year)
        
        popular_scenarios = PlayHistory.objects.filter(
            filters
        ).values(
            'scenario__id',
            'scenario__title',
            'scenario__game_system',
            'scenario__difficulty'
        ).annotate(
            play_count=Count('id'),
            last_played=Max('played_date')
        ).order_by('-play_count')[:10]
        
        # ゲームシステムの表示名を追加
        for scenario in popular_scenarios:
            system_code = scenario['scenario__game_system']
            scenario['game_system_display'] = dict(Scenario.GAME_SYSTEM_CHOICES).get(system_code, system_code)
        
        return list(popular_scenarios)
    
    def _get_system_trends(self, user):
        """ゲームシステム別の年次推移（過去3年）"""
        current_year = timezone.now().year
        start_year = current_year - 2  # 過去3年
        
        trends = {}
        for year in range(start_year, current_year + 1):
            system_stats = PlayHistory.objects.filter(
                user=user,
                played_date__year=year
            ).values('scenario__game_system').annotate(
                count=Count('id')
            )
            
            for stat in system_stats:
                system = stat['scenario__game_system']
                system_name = dict(Scenario.GAME_SYSTEM_CHOICES).get(system, system)
                
                if system_name not in trends:
                    trends[system_name] = {
                        'system_code': system,
                        'system_name': system_name,
                        'data': []
                    }
                
                trends[system_name]['data'].append({
                    'year': year,
                    'count': stat['count']
                })
        
        # 年度が欠けている場合は0で埋める
        for system_data in trends.values():
            existing_years = {d['year'] for d in system_data['data']}
            for year in range(start_year, current_year + 1):
                if year not in existing_years:
                    system_data['data'].append({'year': year, 'count': 0})
            system_data['data'].sort(key=lambda x: x['year'])
        
        return list(trends.values())


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

        # 曜日/時間帯の分布（グラフ用）
        weekly_stats = self._get_weekly_stats(user, year)
        hourly_stats = self._get_hourly_stats(user, year)
        
        return Response({
            'user': {
                'id': user.id,
                'nickname': user.nickname or user.username,
                'trpg_start_year': self._get_trpg_start_year(user),
            },
            'year': year,
            'total_play_time': yearly_stats['total_minutes'],
            'session_count': yearly_stats['total_sessions'],
            'gm_session_count': yearly_stats['gm_sessions'],
            'player_session_count': yearly_stats['pl_sessions'],
            'scenario_count': yearly_stats['played_scenarios'],
            'yearly_stats': yearly_stats,
            'monthly_stats': monthly_stats,
            'system_stats': system_stats,
            'role_stats': role_stats,
            'group_stats': group_stats,
            'recent_sessions': recent_sessions,
            'weekly_stats': weekly_stats,
            'hourly_stats': hourly_stats,
        })

    def _get_weekly_stats(self, user, year):
        """曜日別セッション数（Sun..Sat の順）"""
        sessions = TRPGSession.objects.filter(
            Q(participants=user) | Q(gm=user),
            date__year=year,
            status='completed'
        ).distinct()

        counts = [0] * 7  # 0:Sun ... 6:Sat
        for session in sessions:
            # Python weekday: Mon=0..Sun=6 -> Sun=0..Sat=6
            idx = (session.date.weekday() + 1) % 7
            counts[idx] += 1

        return {
            'counts': counts,
            'total': sum(counts),
        }

    def _get_hourly_stats(self, user, year):
        """時間帯別セッション数（0..23）"""
        sessions = TRPGSession.objects.filter(
            Q(participants=user) | Q(gm=user),
            date__year=year,
            status='completed'
        ).distinct()

        counts = [0] * 24
        for session in sessions:
            counts[session.date.hour] += 1

        return {
            'counts': counts,
            'total': sum(counts),
        }
    
    def _get_yearly_stats(self, user, year):
        """年間統計データ"""
        sessions = TRPGSession.objects.filter(
            (Q(participants=user) | Q(gm=user)),
            date__year=year,
            status='completed'
        ).distinct()
        
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
                (Q(participants=user) | Q(gm=user)),
                date__year=year,
                date__month=month,
                status='completed'
            ).distinct()
            
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
                date__year=year,
                status='completed'
            ).filter(Q(participants=user) | Q(gm=user)).distinct()
            
            session_count = sessions.count()
            total_minutes = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
            total_hours = round(total_minutes / 60, 1)
            average_session_hours = round(total_hours / session_count, 1) if session_count > 0 else 0

            participant_ids = SessionParticipant.objects.filter(
                session__in=sessions,
                user_id__isnull=False,
            ).values_list('user_id', flat=True).distinct()
            gm_ids = sessions.values_list('gm_id', flat=True).distinct()
            active_members = len(set(participant_ids) | set(gm_ids))

            top_gm = sessions.values('gm__nickname', 'gm__username').annotate(
                gm_count=Count('id')
            ).order_by('-gm_count').first()
            
            if session_count > 0:  # アクティブなグループのみ
                group_data.append({
                    'group_id': group.id,
                    'group_name': group.name,
                    'session_count': session_count,
                    'total_hours': total_hours,
                    'average_session_hours': average_session_hours,
                    'active_members': active_members,
                    'total_members': group.members.count(),
                    'top_gm': (top_gm['gm__nickname'] or top_gm['gm__username']) if top_gm else None,
                    'top_gm_sessions': top_gm['gm_count'] if top_gm else 0,
                })
        
        return sorted(group_data, key=lambda x: x['session_count'], reverse=True)
    
    def _get_recent_sessions(self, user, limit=10):
        """最近のセッション履歴"""
        sessions = TRPGSession.objects.filter(
            status='completed'
        ).filter(Q(participants=user) | Q(gm=user)).distinct().select_related('group', 'gm').order_by('-date')[:limit]
        
        result = []
        for session in sessions:
            # ユーザーの役割を取得
            participant = SessionParticipant.objects.filter(
                session=session, user=user
            ).first()
            
            result.append({
                'id': session.id,
                'title': session.title,
                'date': session.date.isoformat() if session.date else None,
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
            participants=user,
            date__isnull=False,
        ).order_by('date').first()
        
        if earliest_session:
            return earliest_session.date.year
        
        return user.date_joined.year
    
    def _calculate_completion_rate(self, user, year):
        """セッション完了率の計算"""
        total_planned = TRPGSession.objects.filter(
            Q(participants=user) | Q(gm=user),
            date__year=year
        ).distinct().count()
        
        completed = TRPGSession.objects.filter(
            Q(participants=user) | Q(gm=user),
            date__year=year,
            status='completed'
        ).distinct().count()
        
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
            date__gte=eight_weeks_ago,
            status='completed'
        ).filter(Q(participants=user) | Q(gm=user)).distinct().order_by('-date')
        
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
            date__year=year,
            status='completed'
        ).filter(Q(participants=user) | Q(gm=user)).distinct().order_by('date')
        
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
            date__year=year,
            status='completed'
        ).filter(Q(participants=user) | Q(gm=user)).distinct()
        
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
            date__year=year,
            status='completed'
        ).filter(Q(participants=user) | Q(gm=user)).distinct()
        
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
        raw_type = request.query_params.get('type')
        ranking_type = request.query_params.get('ranking_type') or raw_type or 'hours'  # hours, sessions, gm
        category = request.query_params.get('category')  # system, scenario
        game_system = request.query_params.get('game_system')
        scenario_id = request.query_params.get('scenario_id') or request.query_params.get('scenario')
        include_trends = request.query_params.get('trends', 'false').lower() == 'true'
        trend_unit = request.query_params.get('trend_unit')

        limit = self._parse_int(request.query_params.get('limit'), default=20, min_value=1, max_value=100)
        category_items = self._parse_int(request.query_params.get('category_items'), default=10, min_value=1, max_value=50)
        trend_periods = self._parse_int(request.query_params.get('trend_periods'), default=None, min_value=1, max_value=120)

        try:
            period = self._parse_period(request)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        base_sessions = self._get_completed_sessions(period['start_at'], period['end_at'])
        filtered_sessions = self._filter_sessions_by_scenario(base_sessions, game_system=game_system, scenario_id=scenario_id)

        if ranking_type not in {'hours', 'sessions', 'gm'}:
            # /api/accounts/export/ などの data_type=ranking と衝突するケースに備えてフォールバック
            if request.query_params.get('ranking_type') is None and raw_type in {'tindalos', 'ranking', 'groups'}:
                ranking_type = 'hours'
            else:
                return Response({'error': 'Invalid ranking type'}, status=status.HTTP_400_BAD_REQUEST)

        ranking, user_stats = self._build_ranking(filtered_sessions, ranking_type, limit=limit)
        users_data = self._build_users_data(ranking, user_stats, request.user)

        response_data = {
            'year': period.get('year', timezone.now().year),
            'month': period.get('month'),
            'period': {
                'type': period['type'],
                'start_date': period['start_at'].isoformat() if period['start_at'] else None,
                'end_date': period['end_at'].isoformat() if period['end_at'] else None,
            },
            'type': ranking_type,
            'ranking': ranking,
            'users': users_data,
        }

        if category in {'system', 'scenario'}:
            response_data['category'] = category
            response_data['category_rankings'] = self._build_category_rankings(
                base_sessions,
                ranking_type=ranking_type,
                category=category,
                limit=limit,
                category_items=category_items,
                game_system=game_system,
                scenario_id=scenario_id,
            )

        if include_trends:
            if trend_unit is None:
                trend_unit = 'year' if period['type'] == 'all' else 'month'
            if trend_unit not in {'month', 'year'}:
                return Response({'error': 'Invalid trend_unit'}, status=status.HTTP_400_BAD_REQUEST)

            response_data['trend_unit'] = trend_unit
            response_data['trends'] = self._build_trends(
                filtered_sessions,
                ranking_type=ranking_type,
                trend_unit=trend_unit,
                limit=limit,
                start_at=period['start_at'],
                end_at=period['end_at'],
                trend_periods=trend_periods,
            )

        return Response(response_data)

    def _parse_int(self, value, default=None, min_value=None, max_value=None):
        if value is None or value == '':
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            raise ValueError(f'Invalid integer: {value}')
        if min_value is not None and parsed < min_value:
            return min_value
        if max_value is not None and parsed > max_value:
            return max_value
        return parsed

    def _parse_period(self, request):
        period_type = request.query_params.get('period')
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        now = timezone.now()
        year_int = self._parse_int(year, default=now.year, min_value=1970, max_value=2100)
        month_int = self._parse_int(month, default=now.month, min_value=1, max_value=12)

        if (start_date or end_date) and period_type in {None, '', 'range'}:
            period_type = 'range'
        if period_type in {None, ''}:
            period_type = 'year'

        if period_type == 'all':
            return {
                'type': 'all',
                'year': year_int,
                'month': None,
                'start_at': None,
                'end_at': None,
            }

        tz = timezone.get_current_timezone()

        if period_type == 'year':
            start_at = timezone.make_aware(datetime(year_int, 1, 1, 0, 0, 0), tz)
            end_at = timezone.make_aware(datetime(year_int, 12, 31, 23, 59, 59, 999999), tz)
            return {
                'type': 'year',
                'year': year_int,
                'month': None,
                'start_at': start_at,
                'end_at': end_at,
            }

        if period_type == 'month':
            last_day = monthrange(year_int, month_int)[1]
            start_at = timezone.make_aware(datetime(year_int, month_int, 1, 0, 0, 0), tz)
            end_at = timezone.make_aware(datetime(year_int, month_int, last_day, 23, 59, 59, 999999), tz)
            return {
                'type': 'month',
                'year': year_int,
                'month': month_int,
                'start_at': start_at,
                'end_at': end_at,
            }

        if period_type != 'range':
            raise ValueError('Invalid period')

        if not start_date or not end_date:
            raise ValueError('start_date and end_date are required for period=range')

        start_at = parse_datetime(start_date) or (
            datetime.combine(parse_date(start_date) or None, datetime.min.time()) if parse_date(start_date) else None
        )
        end_at = parse_datetime(end_date) or (
            datetime.combine(parse_date(end_date) or None, datetime.max.time()) if parse_date(end_date) else None
        )

        if start_at is None or end_at is None:
            raise ValueError('Invalid start_date/end_date format')

        if timezone.is_naive(start_at):
            start_at = timezone.make_aware(start_at, tz)
        if timezone.is_naive(end_at):
            end_at = timezone.make_aware(end_at, tz)

        if start_at > end_at:
            raise ValueError('start_date must be <= end_date')

        return {
            'type': 'range',
            'year': year_int,
            'month': None,
            'start_at': start_at,
            'end_at': end_at,
        }

    def _get_completed_sessions(self, start_at, end_at):
        sessions = TRPGSession.objects.filter(status='completed', date__isnull=False)
        if start_at:
            sessions = sessions.filter(date__gte=start_at)
        if end_at:
            sessions = sessions.filter(date__lte=end_at)
        return sessions

    def _filter_sessions_by_scenario(self, sessions, game_system=None, scenario_id=None):
        if not game_system and not scenario_id:
            return sessions

        play_history = PlayHistory.objects.filter(session__in=sessions, scenario__isnull=False)
        if game_system:
            play_history = play_history.filter(scenario__game_system=game_system)
        if scenario_id:
            play_history = play_history.filter(scenario_id=scenario_id)

        session_ids = play_history.values_list('session_id', flat=True).distinct()
        return sessions.filter(id__in=session_ids)

    def _aggregate_user_stats(self, sessions):
        """セッション集合からユーザー別統計を集計"""
        stats = {}

        gm_rows = sessions.values('gm_id').annotate(
            gm_sessions=Count('id'),
            gm_minutes=Sum('duration_minutes'),
        )
        for row in gm_rows:
            user_id = row['gm_id']
            data = stats.setdefault(user_id, {
                'gm_sessions': 0,
                'gm_minutes': 0,
                'player_sessions': 0,
                'player_minutes': 0,
            })
            data['gm_sessions'] += row['gm_sessions'] or 0
            data['gm_minutes'] += row['gm_minutes'] or 0

        player_rows = SessionParticipant.objects.filter(
            session__in=sessions,
            role='player',
            user_id__isnull=False,
        ).values('user_id').annotate(
            player_sessions=Count('session', distinct=True),
            player_minutes=Sum('session__duration_minutes'),
        )
        for row in player_rows:
            user_id = row['user_id']
            data = stats.setdefault(user_id, {
                'gm_sessions': 0,
                'gm_minutes': 0,
                'player_sessions': 0,
                'player_minutes': 0,
            })
            data['player_sessions'] += row['player_sessions'] or 0
            data['player_minutes'] += row['player_minutes'] or 0

        for data in stats.values():
            data['session_count'] = data['gm_sessions'] + data['player_sessions']
            data['total_minutes'] = data['gm_minutes'] + data['player_minutes']

        return stats

    def _build_ranking(self, sessions, ranking_type, limit=20):
        user_stats = self._aggregate_user_stats(sessions)
        if not user_stats:
            return [], {}

        user_ids = list(user_stats.keys())
        users = CustomUser.objects.filter(id__in=user_ids).values('id', 'nickname', 'username')
        name_map = {u['id']: (u['nickname'] or u['username']) for u in users}

        def sort_key(item):
            user_id, data = item
            if ranking_type == 'hours':
                primary = data['total_minutes']
                secondary = data['session_count']
            elif ranking_type == 'sessions':
                primary = data['session_count']
                secondary = data['total_minutes']
            else:  # gm
                primary = data['gm_sessions']
                secondary = data['gm_minutes']
            return (-primary, -secondary, user_id)

        sorted_items = sorted(user_stats.items(), key=sort_key)[:limit]

        ranking = []
        for rank, (user_id, data) in enumerate(sorted_items, start=1):
            nickname = name_map.get(user_id)
            if ranking_type == 'hours':
                ranking.append({
                    'rank': rank,
                    'user_id': user_id,
                    'nickname': nickname,
                    'total_hours': round((data['total_minutes'] or 0) / 60, 1),
                    'session_count': data['session_count'],
                    'gm_count': data['gm_sessions'],
                })
            elif ranking_type == 'sessions':
                ranking.append({
                    'rank': rank,
                    'user_id': user_id,
                    'nickname': nickname,
                    'session_count': data['session_count'],
                    'total_hours': round((data['total_minutes'] or 0) / 60, 1),
                    'gm_count': data['gm_sessions'],
                })
            else:  # gm
                ranking.append({
                    'rank': rank,
                    'user_id': user_id,
                    'nickname': nickname,
                    'gm_count': data['gm_sessions'],
                    'gm_hours': round((data['gm_minutes'] or 0) / 60, 1),
                })

        return ranking, user_stats

    def _build_users_data(self, ranking, user_stats, current_user):
        ranked_ids = [item['user_id'] for item in ranking]
        users_data = []

        for item in ranking:
            user_id = item['user_id']
            stats = user_stats.get(user_id, {})
            users_data.append({
                'user': {
                    'id': user_id,
                    'nickname': item.get('nickname'),
                },
                'total_play_time': stats.get('total_minutes', 0),
                'session_count': stats.get('session_count', 0),
                'gm_count': stats.get('gm_sessions', 0),
            })

        if current_user.id not in ranked_ids:
            stats = user_stats.get(current_user.id, {
                'total_minutes': 0,
                'session_count': 0,
                'gm_sessions': 0,
            })
            users_data.append({
                'user': {
                    'id': current_user.id,
                    'nickname': current_user.nickname or current_user.username,
                },
                'total_play_time': stats.get('total_minutes', 0),
                'session_count': stats.get('session_count', 0),
                'gm_count': stats.get('gm_sessions', 0),
            })

        return users_data

    def _build_category_rankings(
        self,
        base_sessions,
        ranking_type,
        category,
        limit,
        category_items,
        game_system=None,
        scenario_id=None,
    ):
        if category == 'system':
            systems = [(game_system, dict(Scenario.GAME_SYSTEM_CHOICES).get(game_system, game_system))] if game_system else Scenario.GAME_SYSTEM_CHOICES
            result = []
            for system_code, system_name in systems:
                sessions = self._filter_sessions_by_scenario(base_sessions, game_system=system_code, scenario_id=None)
                ranking, _ = self._build_ranking(sessions, ranking_type, limit=limit)
                if ranking:
                    result.append({
                        'system_code': system_code,
                        'system_name': system_name,
                        'ranking': ranking,
                    })
            return result

        if category == 'scenario':
            if scenario_id:
                scenarios = Scenario.objects.filter(id=scenario_id).values('id', 'title', 'game_system', 'difficulty')
            else:
                history = PlayHistory.objects.filter(
                    session__in=base_sessions,
                    scenario__isnull=False,
                )
                if game_system:
                    history = history.filter(scenario__game_system=game_system)

                top = history.values(
                    'scenario_id',
                    'scenario__title',
                    'scenario__game_system',
                    'scenario__difficulty',
                ).annotate(
                    session_count=Count('session', distinct=True),
                    last_played=Max('played_date'),
                ).order_by('-session_count', '-last_played')[:category_items]
                scenarios = [
                    {
                        'id': row['scenario_id'],
                        'title': row['scenario__title'],
                        'game_system': row['scenario__game_system'],
                        'difficulty': row['scenario__difficulty'],
                    }
                    for row in top
                ]

            result = []
            for scenario in scenarios:
                sessions = self._filter_sessions_by_scenario(base_sessions, scenario_id=scenario['id'], game_system=None)
                ranking, _ = self._build_ranking(sessions, ranking_type, limit=limit)
                if ranking:
                    result.append({
                        'scenario': {
                            'id': scenario['id'],
                            'title': scenario['title'],
                            'game_system': scenario['game_system'],
                            'game_system_display': dict(Scenario.GAME_SYSTEM_CHOICES).get(scenario['game_system'], scenario['game_system']),
                            'difficulty': scenario['difficulty'],
                        },
                        'ranking': ranking,
                    })
            return result

        return []

    def _build_trends(self, sessions, ranking_type, trend_unit, limit, start_at, end_at, trend_periods=None):
        if start_at and end_at:
            trend_start = start_at
            trend_end = end_at
        else:
            # 全期間の場合は直近N期間のみ返す（デフォルト: month=12, year=5）
            now = timezone.now()
            trend_end = now
            if trend_periods is None:
                trend_periods = 12 if trend_unit == 'month' else 5
            trend_start = self._shift_period(trend_end, trend_unit, -(trend_periods - 1))

        if trend_unit == 'month':
            buckets = self._iter_month_buckets(trend_start, trend_end)
        else:
            buckets = self._iter_year_buckets(trend_start, trend_end)

        result = []
        for bucket in buckets:
            bucket_sessions = sessions.filter(date__gte=bucket['start_at'], date__lte=bucket['end_at'])
            ranking, _ = self._build_ranking(bucket_sessions, ranking_type, limit=limit)
            result.append({
                'label': bucket['label'],
                'start_date': bucket['start_at'].isoformat(),
                'end_date': bucket['end_at'].isoformat(),
                'ranking': ranking,
            })

        return result

    def _shift_period(self, dt, unit, offset):
        tz = timezone.get_current_timezone()
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, tz)

        if unit == 'year':
            year = dt.year + offset
            return dt.replace(year=year)

        month = dt.month + offset
        year = dt.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(dt.day, monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    def _iter_month_buckets(self, start_at, end_at):
        tz = timezone.get_current_timezone()
        cursor = start_at.astimezone(tz).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_cursor = end_at.astimezone(tz)

        while cursor <= end_cursor:
            last_day = monthrange(cursor.year, cursor.month)[1]
            month_start = cursor
            month_end = cursor.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)

            bucket_start = max(month_start, start_at)
            bucket_end = min(month_end, end_at)

            yield {
                'label': f"{cursor.year}-{cursor.month:02d}",
                'start_at': bucket_start,
                'end_at': bucket_end,
            }

            cursor = self._shift_period(cursor, 'month', 1)

    def _iter_year_buckets(self, start_at, end_at):
        tz = timezone.get_current_timezone()
        cursor_year = start_at.astimezone(tz).year
        end_year = end_at.astimezone(tz).year

        for year in range(cursor_year, end_year + 1):
            year_start = timezone.make_aware(datetime(year, 1, 1, 0, 0, 0), tz)
            year_end = timezone.make_aware(datetime(year, 12, 31, 23, 59, 59, 999999), tz)

            bucket_start = max(year_start, start_at)
            bucket_end = min(year_end, end_at)

            yield {
                'label': str(year),
                'start_at': bucket_start,
                'end_at': bucket_end,
            }
    
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
            total_hours = stats.get('total_hours', 0)
            group_info = {
                'group': {
                    'id': stats['group_id'],
                    'name': stats['group_name']
                },
                'group_id': stats['group_id'],
                'group_name': stats['group_name'],
                'member_count': stats['total_members'],
                'total_members': stats['total_members'],
                'session_count': stats['session_count'],
                'total_play_time': total_hours * 60,  # 分単位に変換
                'total_hours': total_hours,
                'average_session_hours': stats.get('avg_session_hours', 0),
                'active_members': stats.get('active_members', 0),
                'top_gm': stats.get('top_gm'),
                'top_gm_sessions': stats.get('top_gm_sessions', 0),
                'member_contributions': stats.get('member_contributions', []),
                'popular_scenarios': stats.get('popular_scenarios', []),
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
        
        # アクティブメンバー数（GM + 参加者）
        participant_ids = SessionParticipant.objects.filter(
            session__in=sessions,
            user_id__isnull=False,
        ).values_list('user_id', flat=True).distinct()
        gm_ids = sessions.values_list('gm_id', flat=True).distinct()
        active_members = len(set(participant_ids) | set(gm_ids))
        
        # 最も活発なGM
        top_gm = sessions.values('gm__nickname', 'gm__username').annotate(
            gm_count=Count('id')
        ).order_by('-gm_count').first()

        member_contributions = self._get_member_contributions(group, sessions, session_count=session_count)
        popular_scenarios = self._get_group_popular_scenarios(sessions)

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
            'member_contributions': member_contributions,
            'popular_scenarios': popular_scenarios,
        }

    def _get_group_popular_scenarios(self, sessions):
        """グループ内の人気シナリオランキング"""
        if not sessions.exists():
            return []

        popular_scenarios = PlayHistory.objects.filter(
            session__in=sessions,
            scenario__isnull=False,
        ).values(
            'scenario__id',
            'scenario__title',
            'scenario__game_system',
            'scenario__difficulty',
        ).annotate(
            session_count=Count('session', distinct=True),
            unique_players=Count('user', distinct=True),
            last_played=Max('played_date'),
        ).order_by('-session_count', '-last_played')[:10]

        for scenario in popular_scenarios:
            system_code = scenario['scenario__game_system']
            scenario['game_system_display'] = dict(Scenario.GAME_SYSTEM_CHOICES).get(system_code, system_code)

        return list(popular_scenarios)

    def _get_member_contributions(self, group, sessions, session_count=0):
        """メンバー別の貢献度（GM/PL回数とプレイ時間）"""
        if not sessions.exists():
            return []

        member_ids = set(group.members.values_list('id', flat=True))
        contributions = {
            user_id: {
                'user_id': user_id,
                'nickname': None,
                'gm_sessions': 0,
                'player_sessions': 0,
                'total_sessions': 0,
                'participation_rate': 0,
                'total_play_minutes': 0,
                'total_play_hours': 0,
            }
            for user_id in member_ids
        }

        gm_stats = sessions.values('gm_id').annotate(
            session_count=Count('id'),
            total_minutes=Sum('duration_minutes')
        )
        for gm_stat in gm_stats:
            user_id = gm_stat['gm_id']
            if user_id not in member_ids:
                continue
            data = contributions[user_id]
            gm_sessions = gm_stat['session_count'] or 0
            gm_minutes = gm_stat['total_minutes'] or 0
            data['gm_sessions'] += gm_sessions
            data['total_sessions'] += gm_sessions
            data['total_play_minutes'] += gm_minutes

        player_stats = SessionParticipant.objects.filter(
            session__in=sessions,
            role='player'
        ).values('user_id').annotate(
            session_count=Count('session', distinct=True),
            total_minutes=Sum('session__duration_minutes')
        )
        for player_stat in player_stats:
            user_id = player_stat['user_id']
            if user_id not in member_ids:
                continue
            data = contributions[user_id]
            player_sessions = player_stat['session_count'] or 0
            player_minutes = player_stat['total_minutes'] or 0
            data['player_sessions'] += player_sessions
            data['total_sessions'] += player_sessions
            data['total_play_minutes'] += player_minutes

        if not contributions:
            return []

        users = CustomUser.objects.filter(id__in=contributions.keys()).values(
            'id', 'nickname', 'username'
        )
        name_map = {u['id']: (u['nickname'] or u['username']) for u in users}

        result = []
        for user_id, data in contributions.items():
            data['nickname'] = name_map.get(user_id)
            data['total_play_hours'] = round(data['total_play_minutes'] / 60, 1) if data['total_play_minutes'] else 0
            data['participation_rate'] = round((data['total_sessions'] / session_count) * 100, 1) if session_count > 0 else 0
            result.append(data)

        result.sort(key=lambda item: (-item['total_play_minutes'], -item['total_sessions'], item['user_id']))
        return result


class DetailedTindalosMetricsView(APIView):
    """拡張版Tindalos統計API - 年度・月別詳細集計"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        view_type = request.query_params.get('type', 'summary')
        year = request.query_params.get('year')
        start_year = request.query_params.get('start_year')
        end_year = request.query_params.get('end_year')
        
        if view_type == 'yearly_trends':
            return Response(self._get_yearly_trends_detailed(user, start_year, end_year))
        elif view_type == 'monthly_details':
            if not year:
                year = timezone.now().year
            return Response(self._get_monthly_details_detailed(user, int(year)))
        elif view_type == 'popular_scenarios':
            return Response(self._get_popular_scenarios_detailed(user, year))
        elif view_type == 'system_trends':
            return Response(self._get_system_trends_detailed(user))
        else:
            return Response(self._get_summary_stats(user, year))
    
    def _get_summary_stats(self, user, year=None):
        """総合統計サマリー"""
        if not year:
            year = timezone.now().year
        else:
            year = int(year)
        
        # 基本統計
        session_filter = Q(participants=user) | Q(gm=user)
        session_filter &= Q(date__year=year)
        
        sessions = TRPGSession.objects.filter(session_filter, status='completed').distinct()
        session_count = sessions.count()
        gm_count = sessions.filter(gm=user).count()
        total_minutes = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
        
        # シナリオ統計
        play_history = PlayHistory.objects.filter(user=user, played_date__year=year)
        scenario_count = play_history.values('scenario').distinct().count()
        
        # ゲームシステム別サマリー
        system_stats = play_history.values('scenario__game_system').annotate(
            count=Count('id')
        ).order_by('-count')
        
        systems = []
        for stat in system_stats:
            system_code = stat['scenario__game_system']
            systems.append({
                'system_code': system_code,
                'system_name': dict(Scenario.GAME_SYSTEM_CHOICES).get(system_code, system_code),
                'count': stat['count']
            })
        
        return {
            'year': year,
            'session_count': session_count,
            'gm_session_count': gm_count,
            'player_session_count': session_count - gm_count,
            'total_hours': round(total_minutes / 60, 1),
            'scenario_count': scenario_count,
            'game_systems': systems
        }
    
    def _get_yearly_trends_detailed(self, user, start_year=None, end_year=None):
        """複数年度にわたる詳細統計データ"""
        # 開始年と終了年の決定
        first_history = PlayHistory.objects.filter(user=user).order_by('played_date').first()
        if not first_history:
            return {'years': [], 'message': 'プレイ履歴がありません'}
        
        if not start_year:
            start_year = first_history.played_date.year
        else:
            start_year = int(start_year)
            
        if not end_year:
            end_year = timezone.now().year
        else:
            end_year = int(end_year)
        
        yearly_data = []
        
        for year in range(start_year, end_year + 1):
            # セッション統計
            session_filter = (Q(participants=user) | Q(gm=user)) & Q(date__year=year)
            sessions = TRPGSession.objects.filter(session_filter, status='completed').distinct()
            
            session_count = sessions.count()
            gm_sessions = sessions.filter(gm=user).count()
            total_minutes = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
            
            # シナリオ統計
            scenarios = PlayHistory.objects.filter(
                user=user, 
                played_date__year=year
            ).values('scenario').distinct().count()
            
            # ゲームシステム別集計
            system_breakdown = PlayHistory.objects.filter(
                user=user,
                played_date__year=year
            ).values('scenario__game_system').annotate(
                count=Count('id')
            )
            
            systems = {}
            for item in system_breakdown:
                system_code = item['scenario__game_system']
                system_name = dict(Scenario.GAME_SYSTEM_CHOICES).get(system_code, system_code)
                systems[system_name] = item['count']
            
            yearly_data.append({
                'year': year,
                'sessions': {
                    'total': session_count,
                    'as_gm': gm_sessions,
                    'as_player': session_count - gm_sessions,
                    'total_hours': round(total_minutes / 60, 1)
                },
                'scenarios': scenarios,
                'systems': systems
            })
        
        return {
            'period': f"{start_year} - {end_year}",
            'years': yearly_data,
            'total_years': end_year - start_year + 1
        }
    
    def _get_monthly_details_detailed(self, user, year):
        """月別詳細統計（シナリオ・システム別内訳含む）"""
        monthly_data = []
        months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
        
        for month in range(1, 13):
            # セッション統計
            session_filter = (Q(participants=user) | Q(gm=user)) & Q(date__year=year) & Q(date__month=month)
            sessions = TRPGSession.objects.filter(session_filter, status='completed').distinct()
            
            session_count = sessions.count()
            gm_count = sessions.filter(gm=user).count()
            total_minutes = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
            
            # 月別シナリオランキング
            scenarios = PlayHistory.objects.filter(
                user=user,
                played_date__year=year,
                played_date__month=month
            ).values(
                'scenario__id',
                'scenario__title',
                'scenario__game_system',
                'scenario__difficulty'
            ).annotate(
                play_count=Count('id'),
                as_gm=Count('id', filter=Q(role='gm')),
                as_player=Count('id', filter=Q(role='player'))
            ).order_by('-play_count')[:5]
            
            # ゲームシステム表示名を追加
            scenario_list = []
            for scenario in scenarios:
                system_code = scenario['scenario__game_system']
                scenario_list.append({
                    'id': scenario['scenario__id'],
                    'title': scenario['scenario__title'],
                    'system': dict(Scenario.GAME_SYSTEM_CHOICES).get(system_code, system_code),
                    'difficulty': scenario['scenario__difficulty'],
                    'play_count': scenario['play_count'],
                    'as_gm': scenario['as_gm'],
                    'as_player': scenario['as_player']
                })
            
            monthly_data.append({
                'month': month,
                'month_name': months[month - 1],
                'sessions': {
                    'total': session_count,
                    'as_gm': gm_count,
                    'as_player': session_count - gm_count,
                    'total_hours': round(total_minutes / 60, 1)
                },
                'top_scenarios': scenario_list
            })
        
        return {
            'year': year,
            'months': monthly_data
        }
    
    def _get_popular_scenarios_detailed(self, user, year=None):
        """人気シナリオの詳細ランキング"""
        filters = Q(user=user)
        if year:
            filters &= Q(played_date__year=int(year))
        
        # 基本的なシナリオランキング
        popular = PlayHistory.objects.filter(
            filters
        ).values(
            'scenario__id',
            'scenario__title',
            'scenario__game_system',
            'scenario__difficulty',
            'scenario__author',
            'scenario__summary'
        ).annotate(
            total_plays=Count('id'),
            gm_plays=Count('id', filter=Q(role='gm')),
            player_plays=Count('id', filter=Q(role='player')),
            first_played=Min('played_date'),
            last_played=Max('played_date'),
            unique_sessions=Count('session', distinct=True)
        ).order_by('-total_plays')[:20]
        
        scenarios = []
        for item in popular:
            system_code = item['scenario__game_system']
            scenarios.append({
                'id': item['scenario__id'],
                'title': item['scenario__title'],
                'system': dict(Scenario.GAME_SYSTEM_CHOICES).get(system_code, system_code),
                'difficulty': item['scenario__difficulty'],
                'author': item['scenario__author'],
                'description': item['scenario__summary'][:200] + '...' if len(item['scenario__summary'] or '') > 200 else item['scenario__summary'],
                'stats': {
                    'total_plays': item['total_plays'],
                    'as_gm': item['gm_plays'],
                    'as_player': item['player_plays'],
                    'unique_sessions': item['unique_sessions']
                },
                'dates': {
                    'first_played': item['first_played'].isoformat() if item['first_played'] else None,
                    'last_played': item['last_played'].isoformat() if item['last_played'] else None,
                    'days_between': (item['last_played'] - item['first_played']).days if item['first_played'] and item['last_played'] else 0
                }
            })
        
        return {
            'year': year if year else 'all_time',
            'count': len(scenarios),
            'scenarios': scenarios
        }
    
    def _get_system_trends_detailed(self, user):
        """ゲームシステム別の詳細な年次推移"""
        current_year = timezone.now().year
        
        # 過去5年分のデータを取得
        years_to_analyze = 5
        start_year = current_year - years_to_analyze + 1
        
        # 年度別・システム別の集計
        yearly_system_data = {}
        
        for year in range(start_year, current_year + 1):
            system_stats = PlayHistory.objects.filter(
                user=user,
                played_date__year=year
            ).values('scenario__game_system').annotate(
                count=Count('id'),
                unique_scenarios=Count('scenario', distinct=True),
                as_gm=Count('id', filter=Q(role='gm')),
                as_player=Count('id', filter=Q(role='player'))
            )
            
            for stat in system_stats:
                system_code = stat['scenario__game_system']
                system_name = dict(Scenario.GAME_SYSTEM_CHOICES).get(system_code, system_code)
                
                if system_name not in yearly_system_data:
                    yearly_system_data[system_name] = {
                        'system_code': system_code,
                        'system_name': system_name,
                        'yearly_data': []
                    }
                
                yearly_system_data[system_name]['yearly_data'].append({
                    'year': year,
                    'sessions': stat['count'],
                    'unique_scenarios': stat['unique_scenarios'],
                    'as_gm': stat['as_gm'],
                    'as_player': stat['as_player']
                })
        
        # 年度が欠けている場合は0で埋める
        for system_data in yearly_system_data.values():
            existing_years = {d['year'] for d in system_data['yearly_data']}
            for year in range(start_year, current_year + 1):
                if year not in existing_years:
                    system_data['yearly_data'].append({
                        'year': year,
                        'sessions': 0,
                        'unique_scenarios': 0,
                        'as_gm': 0,
                        'as_player': 0
                    })
            system_data['yearly_data'].sort(key=lambda x: x['year'])
            
            # 統計サマリーを追加
            total_sessions = sum(d['sessions'] for d in system_data['yearly_data'])
            system_data['summary'] = {
                'total_sessions': total_sessions,
                'average_per_year': round(total_sessions / years_to_analyze, 1),
                'trend': self._calculate_trend(system_data['yearly_data'])
            }
        
        return {
            'period': f"{start_year} - {current_year}",
            'systems': list(yearly_system_data.values())
        }
    
    def _calculate_trend(self, yearly_data):
        """トレンドを計算（増加/減少/横ばい）"""
        if len(yearly_data) < 2:
            return 'insufficient_data'
        
        # 最近2年の比較
        recent_years = sorted(yearly_data, key=lambda x: x['year'])[-2:]
        prev_count = recent_years[0]['sessions']
        curr_count = recent_years[1]['sessions']
        
        if curr_count > prev_count * 1.2:
            return 'increasing'
        elif curr_count < prev_count * 0.8:
            return 'decreasing'
        else:
            return 'stable'
