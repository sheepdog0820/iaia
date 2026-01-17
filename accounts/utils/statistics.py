"""
統計計算の共通ユーティリティ - コード重複の共通化
"""
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta


class SessionStatistics:
    """セッション統計計算のユーティリティクラス"""
    
    @staticmethod
    def calculate_session_stats(sessions_queryset, user=None):
        """基本的なセッション統計を計算"""
        stats = {
            'total_sessions': sessions_queryset.count(),
            'total_minutes': sessions_queryset.aggregate(
                total=Sum('duration_minutes')
            )['total'] or 0,
        }
        
        # 時間計算
        stats['total_hours'] = round(stats['total_minutes'] / 60, 1) if stats['total_minutes'] > 0 else 0.0
        
        # ユーザー別統計
        if user:
            stats['gm_count'] = sessions_queryset.filter(gm=user).count()
            stats['pl_count'] = stats['total_sessions'] - stats['gm_count']
        
        return stats
    
    @staticmethod
    def calculate_yearly_stats(sessions_queryset, year=None, user=None):
        """年別セッション統計を計算"""
        if year is None:
            year = datetime.now().year
        
        yearly_sessions = sessions_queryset.filter(
            date__year=year,
            status='completed'
        )
        
        return SessionStatistics.calculate_session_stats(yearly_sessions, user)
    
    @staticmethod
    def calculate_monthly_breakdown(sessions_queryset, year=None):
        """月別内訳統計を計算"""
        if year is None:
            year = datetime.now().year
        
        monthly_stats = []
        
        for month in range(1, 13):
            month_sessions = sessions_queryset.filter(
                date__year=year,
                date__month=month,
                status='completed'
            )
            
            stats = SessionStatistics.calculate_session_stats(month_sessions)
            stats['month'] = month
            stats['month_name'] = datetime(year, month, 1).strftime('%B')
            
            monthly_stats.append(stats)
        
        return monthly_stats
    
    @staticmethod
    def calculate_role_distribution(sessions_queryset, user):
        """役割別セッション分布を計算"""
        gm_sessions = sessions_queryset.filter(gm=user)
        pl_sessions = sessions_queryset.filter(participants=user).exclude(gm=user)
        
        gm_stats = SessionStatistics.calculate_session_stats(gm_sessions)
        pl_stats = SessionStatistics.calculate_session_stats(pl_sessions)
        
        return {
            'gm_stats': gm_stats,
            'pl_stats': pl_stats,
            'total_unique_sessions': sessions_queryset.filter(
                Q(gm=user) | Q(participants=user)
            ).distinct().count()
        }


class CharacterStatistics:
    """キャラクター統計計算のユーティリティクラス"""
    
    @staticmethod
    def calculate_character_stats(characters_queryset):
        """基本的なキャラクター統計を計算"""
        stats = {
            'total_characters': characters_queryset.count(),
            'active_characters': characters_queryset.filter(is_active=True).count(),
            'sixth_edition_count': characters_queryset.filter(edition='6th').count(),
        }
        
        stats['inactive_characters'] = stats['total_characters'] - stats['active_characters']
        
        # エディション別分布
        edition_breakdown = characters_queryset.values('edition').annotate(
            count=Count('id')
        ).order_by('edition')
        
        stats['edition_breakdown'] = {
            item['edition']: item['count'] for item in edition_breakdown
        }
        
        return stats
    
    @staticmethod
    def calculate_skill_statistics(skills_queryset):
        """技能統計を計算"""
        stats = {
            'total_skills': skills_queryset.count(),
            'average_skill_value': skills_queryset.aggregate(
                avg=Avg('current_value')
            )['avg'] or 0,
        }
        
        # カテゴリ別分布
        category_breakdown = skills_queryset.values('category').annotate(
            count=Count('id'),
            avg_value=Avg('current_value')
        ).order_by('category')
        
        stats['category_breakdown'] = {
            item['category']: {
                'count': item['count'],
                'average_value': round(item['avg_value'] or 0, 1)
            }
            for item in category_breakdown
        }
        
        # 高技能値（70以上）のカウント
        stats['high_skill_count'] = skills_queryset.filter(current_value__gte=70).count()
        
        return stats


class GroupStatistics:
    """グループ統計計算のユーティリティクラス"""
    
    @staticmethod
    def calculate_group_stats(groups_queryset, user=None):
        """基本的なグループ統計を計算"""
        stats = {
            'total_groups': groups_queryset.count(),
            'public_groups': groups_queryset.filter(visibility='public').count(),
            'private_groups': groups_queryset.filter(visibility='private').count(),
        }
        
        # ユーザー参加統計
        if user:
            user_groups = groups_queryset.filter(members=user)
            stats['user_groups_count'] = user_groups.count()
            stats['user_admin_groups'] = user_groups.filter(
                groupmembership__user=user,
                groupmembership__role='admin'
            ).count()
        
        # メンバー数統計
        member_stats = groups_queryset.aggregate(
            total_members=Sum('members__count'),
            avg_members=Avg('members__count')
        )
        
        stats['total_memberships'] = member_stats['total_members'] or 0
        stats['average_group_size'] = round(member_stats['avg_members'] or 0, 1)
        
        return stats


class ExportStatistics:
    """エクスポート統計計算のユーティリティクラス"""
    
    @staticmethod
    def prepare_export_data(user, year=None):
        """エクスポート用の統合統計データを準備"""
        from schedules.models import TRPGSession
        from ..character_models import CharacterSheet
        from ..models import Group
        
        if year is None:
            year = datetime.now().year
        
        # セッション統計
        user_sessions = TRPGSession.objects.filter(
            Q(gm=user) | Q(participants=user)
        ).distinct()
        
        session_stats = SessionStatistics.calculate_yearly_stats(user_sessions, year, user)
        monthly_stats = SessionStatistics.calculate_monthly_breakdown(user_sessions, year)
        role_stats = SessionStatistics.calculate_role_distribution(user_sessions, user)
        
        # キャラクター統計
        user_characters = CharacterSheet.objects.filter(user=user)
        character_stats = CharacterStatistics.calculate_character_stats(user_characters)
        
        # グループ統計
        user_groups = Group.objects.filter(members=user)
        group_stats = GroupStatistics.calculate_group_stats(user_groups, user)

        dated_sessions = user_sessions.exclude(date__isnull=True)
        first_session = dated_sessions.order_by('date').first()
        latest_session = dated_sessions.order_by('-date').first()
        
        return {
            'user_info': {
                'username': user.username,
                'nickname': user.nickname or user.username,
                'export_date': timezone.now().isoformat(),
                'target_year': year
            },
            'session_statistics': session_stats,
            'monthly_breakdown': monthly_stats,
            'role_distribution': role_stats,
            'character_statistics': character_stats,
            'group_statistics': group_stats,
            'summary': {
                'total_activity_years': user_sessions.dates('date', 'year').count(),
                'first_session_date': first_session.date.isoformat() if first_session and first_session.date else None,
                'latest_session_date': latest_session.date.isoformat() if latest_session and latest_session.date else None,
            }
        }


class TindalosMetrics:
    """Tindalos 形式の統計計算ユーティリティ"""
    
    @staticmethod
    def calculate_tindalos_format(user, year=None):
        """Tindalos 形式での統計データを計算"""
        from schedules.models import TRPGSession
        
        if year is None:
            year = datetime.now().year
        
        # Tindalos 形式の基本統計
        user_sessions = TRPGSession.objects.filter(
            Q(gm=user) | Q(participants=user),
            date__year=year,
            status='completed'
        ).distinct()
        
        gm_sessions = user_sessions.filter(gm=user)
        pl_sessions = user_sessions.filter(participants=user).exclude(gm=user)
        
        # 効率性メトリクス
        total_hours = (user_sessions.aggregate(
            total=Sum('duration_minutes')
        )['total'] or 0) / 60
        
        efficiency_score = 0
        if total_hours > 0:
            sessions_per_hour = user_sessions.count() / total_hours
            efficiency_score = min(sessions_per_hour * 10, 100)  # 最大100点
        
        return {
            'year': year,
            'total_sessions': user_sessions.count(),
            'gm_sessions': gm_sessions.count(),
            'pl_sessions': pl_sessions.count(),
            'total_hours': round(total_hours, 1),
            'efficiency_score': round(efficiency_score, 1),
            'activity_level': TindalosMetrics._calculate_activity_level(user_sessions.count()),
            'balance_score': TindalosMetrics._calculate_balance_score(
                gm_sessions.count(), 
                pl_sessions.count()
            ),
            'consistency_score': TindalosMetrics._calculate_consistency_score(user_sessions, year)
        }
    
    @staticmethod
    def _calculate_activity_level(session_count):
        """活動レベルを計算"""
        if session_count >= 50:
            return "very_high"
        elif session_count >= 30:
            return "high"
        elif session_count >= 15:
            return "medium"
        elif session_count >= 5:
            return "low"
        else:
            return "very_low"
    
    @staticmethod
    def _calculate_balance_score(gm_count, pl_count):
        """GM/PL バランススコアを計算"""
        total = gm_count + pl_count
        if total == 0:
            return 0
        
        # 理想的なバランスは GM:PL = 1:2 程度
        ideal_gm_ratio = 1/3
        actual_gm_ratio = gm_count / total
        
        # 理想からの乖離を計算（0-100点）
        deviation = abs(actual_gm_ratio - ideal_gm_ratio)
        balance_score = max(0, 100 - (deviation * 300))
        
        return round(balance_score, 1)
    
    @staticmethod
    def _calculate_consistency_score(sessions_queryset, year):
        """一貫性スコアを計算（月ごとの活動の均等性）"""
        monthly_counts = []
        
        for month in range(1, 13):
            month_count = sessions_queryset.filter(
                date__year=year,
                date__month=month
            ).count()
            monthly_counts.append(month_count)
        
        if sum(monthly_counts) == 0:
            return 0
        
        # 標準偏差を使って一貫性を計算
        import statistics
        try:
            mean_count = statistics.mean(monthly_counts)
            if mean_count == 0:
                return 0
            
            std_dev = statistics.stdev(monthly_counts)
            coefficient_of_variation = std_dev / mean_count
            
            # 変動係数が小さいほど一貫性が高い
            consistency_score = max(0, 100 - (coefficient_of_variation * 50))
            return round(consistency_score, 1)
            
        except statistics.StatisticsError:
            return 0
