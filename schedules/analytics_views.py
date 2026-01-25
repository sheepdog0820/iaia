from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Group
from .models import SessionOccurrence
from .views import _visible_sessions_for


def _display_name(user) -> str:
    return user.nickname or user.username


@dataclass(frozen=True)
class _DateRange:
    start: datetime
    end_exclusive: datetime


def _parse_date_range(params) -> _DateRange:
    now = timezone.now()

    start_raw = params.get('start_date')
    end_raw = params.get('end_date')

    end_date = None
    if end_raw:
        try:
            end_date = date.fromisoformat(end_raw)
        except ValueError:
            end_date = None

    if not end_date:
        end_date = now.date()

    start_date = None
    if start_raw:
        try:
            start_date = date.fromisoformat(start_raw)
        except ValueError:
            start_date = None

    if not start_date:
        start_date = end_date - timedelta(days=365)

    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
    end_exclusive_dt = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min), tz)
    return _DateRange(start=start_dt, end_exclusive=end_exclusive_dt)


class SessionAnalyticsDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        date_range = _parse_date_range(request.query_params)

        group_id_raw = request.query_params.get('group_id')
        group = None
        if group_id_raw:
            try:
                group_id = int(group_id_raw)
            except (TypeError, ValueError):
                return Response({'error': 'group_id must be an integer'}, status=400)

            group = Group.objects.filter(id=group_id).first()
            if not group:
                return Response({'error': 'Group not found'}, status=404)

            if not group.members.filter(id=user.id).exists():
                return Response({'error': 'Permission denied'}, status=403)

        visible_sessions = _visible_sessions_for(user)
        if group is not None:
            visible_sessions = visible_sessions.filter(group_id=group.id)

        occurrences_qs = (
            SessionOccurrence.objects.filter(
                session__in=visible_sessions,
                start_at__gte=date_range.start,
                start_at__lt=date_range.end_exclusive,
            )
            .select_related('session', 'session__gm', 'session__group')
            .prefetch_related('session__sessionparticipant_set__user')
            .order_by('start_at', 'id')
        )

        occurrences_count = occurrences_qs.count()
        sessions_count = occurrences_qs.values('session_id').distinct().count()

        aggregates = occurrences_qs.aggregate(
            total_minutes=Sum('session__duration_minutes'),
        )
        total_minutes = int(aggregates['total_minutes'] or 0)
        total_hours = round(total_minutes / 60, 1) if total_minutes else 0.0

        group_member_count = group.members.count() if group is not None else None

        hour_buckets: dict[int, int] = defaultdict(int)
        user_occurrence_counts: dict[int, int] = defaultdict(int)
        user_meta: dict[int, Any] = {}
        pair_counts: dict[tuple[int, int], int] = defaultdict(int)
        participant_total = 0
        participation_rate_total = 0.0

        occurrences = list(occurrences_qs)
        for occurrence in occurrences:
            session = occurrence.session
            participants = [
                p.user
                for p in session.sessionparticipant_set.all()
                if p.user_id is not None
            ]
            users = [session.gm] + participants

            unique_users = {}
            for u in users:
                unique_users[u.id] = u

            user_ids = sorted(unique_users.keys())
            participant_count = len(user_ids)
            participant_total += participant_count

            if group_member_count:
                participation_rate_total += participant_count / max(group_member_count, 1)

            local_hour = timezone.localtime(occurrence.start_at).hour
            hour_buckets[local_hour] += 1

            for user_id in user_ids:
                user_occurrence_counts[user_id] += 1
                if user_id not in user_meta:
                    user_meta[user_id] = unique_users[user_id]

            for i, a in enumerate(user_ids):
                for b in user_ids[i + 1:]:
                    pair_counts[(a, b)] += 1

        avg_participants = round(participant_total / occurrences_count, 1) if occurrences_count else 0.0
        avg_participation_rate = (
            round(participation_rate_total / occurrences_count * 100, 1)
            if occurrences_count and group_member_count
            else None
        )
        avg_duration_minutes = round(total_minutes / occurrences_count, 1) if occurrences_count else 0.0

        popular_hours = [
            {'hour': hour, 'count': hour_buckets[hour]}
            for hour in sorted(hour_buckets.keys())
        ]

        monthly_trend_qs = (
            occurrences_qs.annotate(month=TruncMonth('start_at'))
            .values('month')
            .annotate(
                occurrences=Count('id'),
                total_minutes=Sum('session__duration_minutes'),
            )
            .order_by('month')
        )
        monthly_trend = []
        for row in monthly_trend_qs:
            month = row['month']
            month_key = month.strftime('%Y-%m') if month else None
            minutes = int(row['total_minutes'] or 0)
            monthly_trend.append({
                'month': month_key,
                'occurrences': int(row['occurrences'] or 0),
                'total_hours': round(minutes / 60, 1) if minutes else 0.0,
            })

        gm_load_qs = (
            occurrences_qs.values('session__gm_id', 'session__gm__username', 'session__gm__nickname')
            .annotate(
                occurrences=Count('id'),
                total_minutes=Sum('session__duration_minutes'),
            )
            .order_by('-total_minutes', '-occurrences')
        )
        gm_load = []
        for row in gm_load_qs:
            gm_id = row['session__gm_id']
            gm_name = row['session__gm__nickname'] or row['session__gm__username']
            minutes = int(row['total_minutes'] or 0)
            gm_load.append({
                'gm_id': gm_id,
                'gm_name': gm_name,
                'occurrences': int(row['occurrences'] or 0),
                'total_hours': round(minutes / 60, 1) if minutes else 0.0,
            })

        top_pairs = []
        for (a, b), count in sorted(pair_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))[:30]:
            user_a = user_meta.get(a)
            user_b = user_meta.get(b)
            top_pairs.append({
                'user1_id': a,
                'user1_name': _display_name(user_a) if user_a else str(a),
                'user2_id': b,
                'user2_name': _display_name(user_b) if user_b else str(b),
                'occurrences_together': count,
            })

        member_participation = []
        for user_id, count in sorted(user_occurrence_counts.items(), key=lambda item: (-item[1], item[0])):
            member_participation.append({
                'user_id': user_id,
                'name': _display_name(user_meta[user_id]) if user_id in user_meta else str(user_id),
                'occurrences': count,
                'participation_rate': (
                    round(count / max(occurrences_count, 1) * 100, 1) if occurrences_count else 0.0
                ),
            })

        return Response({
            'summary': {
                'sessions_count': sessions_count,
                'occurrences_count': occurrences_count,
                'total_hours': total_hours,
                'total_minutes': total_minutes,
                'avg_duration_minutes': avg_duration_minutes,
                'avg_participants': avg_participants,
                'avg_participation_rate': avg_participation_rate,
                'group_member_count': group_member_count,
            },
            'popular_hours': popular_hours,
            'monthly_trend': monthly_trend,
            'gm_load': gm_load,
            'top_pairs': top_pairs,
            'member_participation': member_participation,
        })

