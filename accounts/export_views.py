from schedules.duration import effective_duration_expression

"""
統計データエクスポート機能
"""
import csv
import json
import logging
from io import StringIO

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer, BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .statistics_views import GroupStatisticsView, TindalosMetricsView, UserRankingView

logger = logging.getLogger(__name__)


class InvalidDateParameterError(ValueError):
    """Raised when statistics export date query parameters are invalid."""


class PassthroughCSVRenderer(BaseRenderer):
    media_type = "text/csv"
    format = "csv"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class ExportStatisticsView(APIView):
    """統計データエクスポートビュー"""

    permission_classes = [IsAuthenticated]
    renderer_classes = [
        JSONRenderer,
        BrowsableAPIRenderer,
        PassthroughCSVRenderer,
    ]

    def get(self, request):
        """エクスポート形式とデータタイプに基づいてデータをエクスポート"""
        export_format = request.query_params.get("format", "csv")  # csv, json
        data_type = request.query_params.get("type", "tindalos")  # tindalos, ranking, groups
        year = request.query_params.get("year", timezone.now().year)

        if data_type == "tindalos":
            return self._export_tindalos_metrics(request, export_format, year)
        elif data_type == "ranking":
            return self._export_ranking(request, export_format, year)
        elif data_type == "groups":
            return self._export_groups(request, export_format, year)
        else:
            return JsonResponse({"error": "Invalid data type"}, status=400)

    def _export_tindalos_metrics(self, request, export_format, year):
        """Tindalos Metricsデータのエクスポート"""
        # TindalosMetricsViewからデータを取得
        metrics_view = TindalosMetricsView()
        metrics_view.request = request
        response = metrics_view.get(request)
        data = response.data

        if export_format == "csv":
            return self._export_tindalos_csv(data, year)
        elif export_format == "json":
            return self._export_tindalos_json(data, year)
        else:
            return JsonResponse({"error": "未対応の形式です。対応形式: JSON, CSV"}, status=400)

    def _export_tindalos_csv(self, data, year):
        """Tindalos MetricsをCSV形式でエクスポート"""
        output = StringIO()
        writer = csv.writer(output)

        # ヘッダー情報
        writer.writerow(["タブレノ - Tindalos Metrics Export"])
        writer.writerow([f"Year: {year}"])
        writer.writerow([f'User: {data["user"]["nickname"]}'])
        writer.writerow([f'Export Date: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([])

        # 年間統計
        writer.writerow(["Annual Statistics"])
        yearly_stats = data["yearly_stats"]
        for key, value in yearly_stats.items():
            if isinstance(value, dict):
                writer.writerow([key, json.dumps(value, ensure_ascii=False)])
            else:
                writer.writerow([key, value])
        writer.writerow([])

        # 月別統計
        writer.writerow(["Monthly Statistics"])
        writer.writerow(["Month", "Session Count", "Total Hours", "GM Count", "PL Count"])
        for month_data in data["monthly_stats"]:
            writer.writerow(
                [
                    month_data["month"],
                    month_data["session_count"],
                    month_data["total_hours"],
                    month_data["gm_count"],
                    month_data["pl_count"],
                ]
            )
        writer.writerow([])

        # システム別統計
        writer.writerow(["System Statistics"])
        writer.writerow(["System", "System Name", "Session Count", "Total Hours"])
        for system_data in data["system_stats"]:
            writer.writerow(
                [
                    system_data["system"],
                    system_data["system_name"],
                    system_data["session_count"],
                    system_data["total_hours"],
                ]
            )
        writer.writerow([])

        # 最近のセッション
        writer.writerow(["Recent Sessions"])
        writer.writerow(["Title", "Date", "Duration Hours", "Group", "GM", "Role", "Character"])
        for session in data["recent_sessions"]:
            writer.writerow(
                [
                    session["title"],
                    session["date"],
                    session["duration_hours"],
                    session["group_name"],
                    session["gm_name"],
                    session["role"],
                    session["character_name"],
                ]
            )

        # HTTPレスポンスの作成
        response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="tindalos_metrics_{year}_{timezone.now().strftime("%Y%m%d")}.csv"'
        )
        return response

    def _export_tindalos_json(self, data, year):
        """Tindalos MetricsをJSON形式でエクスポート"""
        export_data = {
            "export_info": {
                "type": "tindalos_metrics",
                "year": year,
                "export_date": timezone.now().isoformat(),
                "user": data["user"]["nickname"],
            },
            "data": data,
        }

        response = HttpResponse(
            json.dumps(export_data, ensure_ascii=False, indent=2), content_type="application/json; charset=utf-8"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="tindalos_metrics_{year}_{timezone.now().strftime("%Y%m%d")}.json"'
        )
        return response

    def _export_ranking(self, request, export_format, year):
        """ランキングデータのエクスポート"""
        ranking_view = UserRankingView()
        ranking_view.request = request
        response = ranking_view.get(request)
        data = response.data

        if export_format == "csv":
            return self._export_ranking_csv(data, year)
        elif export_format == "json":
            return self._export_ranking_json(data, year)
        else:
            return JsonResponse({"error": "未対応の形式です。対応形式: JSON, CSV"}, status=400)

    def _export_ranking_csv(self, data, year):
        """ランキングをCSV形式でエクスポート"""
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(["タブレノ - User Ranking Export"])
        writer.writerow([f"Year: {year}"])
        writer.writerow([f'Type: {data["type"]}'])
        writer.writerow([f'Export Date: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([])

        writer.writerow(["Rank", "User ID", "Nickname", "Total Hours", "Session Count"])
        for user_data in data["ranking"]:
            writer.writerow(
                [
                    user_data["rank"],
                    user_data["user_id"],
                    user_data["nickname"],
                    user_data["total_hours"],
                    user_data["session_count"],
                ]
            )

        response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="user_ranking_{data["type"]}_{year}_{timezone.now().strftime("%Y%m%d")}.csv"'
        )
        return response

    def _export_ranking_json(self, data, year):
        """ランキングをJSON形式でエクスポート"""
        export_data = {
            "export_info": {
                "type": "user_ranking",
                "ranking_type": data["type"],
                "year": year,
                "export_date": timezone.now().isoformat(),
            },
            "data": data,
        }

        response = HttpResponse(
            json.dumps(export_data, ensure_ascii=False, indent=2), content_type="application/json; charset=utf-8"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="user_ranking_{data["type"]}_{year}_{timezone.now().strftime("%Y%m%d")}.json"'
        )
        return response

    def _export_groups(self, request, export_format, year):
        """グループ統計データのエクスポート"""
        groups_view = GroupStatisticsView()
        groups_view.request = request
        response = groups_view.get(request)
        data = response.data

        if export_format == "csv":
            return self._export_groups_csv(data, year)
        elif export_format == "json":
            return self._export_groups_json(data, year)
        else:
            return JsonResponse({"error": "未対応の形式です。対応形式: JSON, CSV"}, status=400)

    def _export_groups_csv(self, data, year):
        """グループ統計をCSV形式でエクスポート"""
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(["タブレノ - Group Statistics Export"])
        writer.writerow([f"Year: {year}"])
        writer.writerow([f'Export Date: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([])

        writer.writerow(
            [
                "Group ID",
                "Group Name",
                "Session Count",
                "Total Hours",
                "Active Members",
                "Total Members",
                "Top GM",
                "Top GM Sessions",
            ]
        )
        for group_data in data["groups"]:
            writer.writerow(
                [
                    group_data["group_id"],
                    group_data["group_name"],
                    group_data["session_count"],
                    group_data["total_hours"],
                    group_data["active_members"],
                    group_data["total_members"],
                    group_data["top_gm"],
                    group_data["top_gm_sessions"],
                ]
            )

        response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="group_statistics_{year}_{timezone.now().strftime("%Y%m%d")}.csv"'
        )
        return response

    def _export_groups_json(self, data, year):
        """グループ統計をJSON形式でエクスポート"""
        export_data = {
            "export_info": {"type": "group_statistics", "year": year, "export_date": timezone.now().isoformat()},
            "data": data,
        }

        response = HttpResponse(
            json.dumps(export_data, ensure_ascii=False, indent=2), content_type="application/json; charset=utf-8"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="group_statistics_{year}_{timezone.now().strftime("%Y%m%d")}.json"'
        )
        return response


class ExportAvailableFormatsView(APIView):
    """利用可能なエクスポート形式を返すビュー"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """利用可能なエクスポート形式とデータタイプを返す"""
        return Response(
            {
                "formats": {
                    "csv": {"name": "CSV", "description": "カンマ区切り値形式（Excel等で開けます）", "available": True},
                    "json": {
                        "name": "JSON",
                        "description": "JSON形式（プログラムでの処理に適しています）",
                        "available": True,
                    },
                },
                "data_types": {
                    "tindalos": {"name": "Tindalos Metrics", "description": "個人の年間プレイ統計"},
                    "ranking": {"name": "User Ranking", "description": "ユーザーランキング"},
                    "groups": {"name": "Group Statistics", "description": "グループ活動統計"},
                },
            }
        )


# 新仕様のエクスポート機能 - ISSUE-002対応
class StatisticsExportView(APIView):
    """統計データエクスポートビュー（新仕様）"""

    permission_classes = [IsAuthenticated]
    renderer_classes = [
        JSONRenderer,
        BrowsableAPIRenderer,
        PassthroughCSVRenderer,
    ]

    def get(self, request):
        """
        統計データのエクスポート
        /api/accounts/export/statistics/

        パラメータ:
        - format: json, csv (デフォルト: json)
        - start_date: YYYY-MM-DD (開始日)
        - end_date: YYYY-MM-DD (終了日)
        """
        export_format = request.query_params.get("format", "json")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # フォーマットの検証
        if export_format not in ["json", "csv"]:
            return Response({"error": "未対応の形式です。対応形式: JSON, CSV"}, status=400)

        # 統計データの収集
        try:
            statistics_data = self._collect_user_statistics(request.user, start_date, end_date)
        except InvalidDateParameterError as e:
            return Response({"error": str(e)}, status=400)
        except Exception:
            logger.exception("Error collecting statistics export data")
            return Response({"error": "Error collecting statistics"}, status=500)

        # フォーマット別エクスポート
        try:
            if export_format == "json":
                return self._export_json(statistics_data)
            elif export_format == "csv":
                return self._export_csv(statistics_data)
        except Exception:
            logger.exception("Error exporting statistics data")
            return Response({"error": "Error exporting data"}, status=500)

    def _collect_user_statistics(self, user, start_date, end_date):
        """ユーザーの統計データを収集"""
        # 日付フィルタの解析
        date_filter, start_date_parsed, end_date_parsed = self._parse_date_filters(start_date, end_date)

        # セッション統計の収集
        session_stats = self._collect_session_statistics(user, date_filter)

        # プレイ履歴データの収集
        play_history_details = self._collect_play_history_data(
            user, start_date_parsed, end_date_parsed, start_date, end_date
        )

        # セッション内訳統計の収集
        session_breakdown = self._collect_session_breakdown_stats(user, date_filter)

        # シナリオ統計の収集
        scenario_stats = self._collect_scenario_statistics(
            user, start_date_parsed, end_date_parsed, start_date, end_date
        )

        # レスポンスのフォーマット
        return self._format_statistics_response(
            user, start_date, end_date, session_stats, play_history_details, session_breakdown, scenario_stats
        )

    def _parse_date_filters(self, start_date, end_date):
        """日付フィルタを解析してQuerySetフィルタを作成"""
        from datetime import datetime

        from django.db.models import Q

        date_filter = Q()
        start_date_parsed = None
        end_date_parsed = None

        if start_date:
            try:
                start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
                date_filter &= Q(date__gte=start_date_parsed)
            except ValueError:
                raise InvalidDateParameterError("Invalid start_date format. Use YYYY-MM-DD")

        if end_date:
            try:
                end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d").date()
                date_filter &= Q(date__lte=end_date_parsed)
            except ValueError:
                raise InvalidDateParameterError("Invalid end_date format. Use YYYY-MM-DD")

        return date_filter, start_date_parsed, end_date_parsed

    def _collect_session_statistics(self, user, date_filter):
        """セッション関連の基本統計を収集"""
        from django.db.models import Count, Q, Sum

        from schedules.models import TRPGSession

        user_sessions = (
            TRPGSession.objects.filter(Q(participants=user) | Q(gm=user), status="completed")
            .filter(date_filter)
            .distinct()
        )

        total_sessions = user_sessions.count()
        total_play_time = (
            user_sessions.aggregate(total_minutes=Sum(effective_duration_expression()))["total_minutes"] or 0
        )

        gm_sessions = user_sessions.filter(gm=user).count()
        player_sessions = total_sessions - gm_sessions

        return {
            "total_sessions": total_sessions,
            "total_play_time": total_play_time,
            "gm_sessions": gm_sessions,
            "player_sessions": player_sessions,
            "user_sessions": user_sessions,
        }

    def _collect_play_history_data(self, user, start_date_parsed, end_date_parsed, start_date, end_date):
        """プレイ履歴の詳細データを収集"""
        from datetime import datetime

        from scenarios.models import PlayHistory

        play_histories = PlayHistory.objects.filter(user=user)
        if start_date or end_date:
            play_histories = play_histories.filter(
                played_date__date__gte=start_date_parsed if start_date else datetime.min.date(),
                played_date__date__lte=end_date_parsed if end_date else datetime.max.date(),
            )

        play_history_details = []
        for history in play_histories.select_related("scenario", "session"):
            session = history.session
            play_history_details.append(
                {
                    "scenario_title": history.scenario.title if history.scenario else "Unknown",
                    "session_title": session.title if session else "Unknown",
                    "played_date": history.played_date.isoformat(),
                    "role": history.role,
                    "duration_minutes": session.effective_duration_minutes if session else 0,
                    "game_system": history.scenario.game_system if history.scenario else "unknown",
                    "group_name": session.group.name if session and session.group else "No Group",
                    "notes": history.notes,
                }
            )

        return play_history_details

    def _collect_session_breakdown_stats(self, user, date_filter):
        """セッション内訳統計を収集（年別・システム別・月別）"""
        from django.db.models import Q

        from schedules.models import TRPGSession

        user_sessions = (
            TRPGSession.objects.filter(Q(participants=user) | Q(gm=user), status="completed")
            .filter(date_filter)
            .select_related("scenario")
            .distinct()
        )

        session_stats = {"by_year": {}, "by_game_system": {}, "by_month": {}}

        for session in user_sessions:
            duration_minutes = session.effective_duration_minutes or 0
            game_system = session.scenario.game_system if session.scenario else "unknown"
            if game_system not in session_stats["by_game_system"]:
                session_stats["by_game_system"][game_system] = {"session_count": 0, "total_minutes": 0}
            session_stats["by_game_system"][game_system]["session_count"] += 1
            session_stats["by_game_system"][game_system]["total_minutes"] += duration_minutes

            if session.date is None:
                continue

            year = session.date.year
            if year not in session_stats["by_year"]:
                session_stats["by_year"][year] = {"session_count": 0, "total_minutes": 0}
            session_stats["by_year"][year]["session_count"] += 1
            session_stats["by_year"][year]["total_minutes"] += duration_minutes

            month = session.date.strftime("%Y-%m")
            if month not in session_stats["by_month"]:
                session_stats["by_month"][month] = {"session_count": 0, "total_minutes": 0}
            session_stats["by_month"][month]["session_count"] += 1
            session_stats["by_month"][month]["total_minutes"] += duration_minutes

        return session_stats

    def _collect_scenario_statistics(self, user, start_date_parsed, end_date_parsed, start_date, end_date):
        """シナリオ関連統計を収集"""
        from datetime import datetime

        from scenarios.models import PlayHistory

        play_histories = PlayHistory.objects.filter(user=user)
        if start_date or end_date:
            play_histories = play_histories.filter(
                played_date__date__gte=start_date_parsed if start_date else datetime.min.date(),
                played_date__date__lte=end_date_parsed if end_date else datetime.max.date(),
            )

        scenarios_played = play_histories.values("scenario").distinct().count()

        # システム別集計
        system_counts = {}
        for history in play_histories:
            if history.scenario:
                system = history.scenario.game_system
                system_counts[system] = system_counts.get(system, 0) + 1

        favorite_systems = [
            {"system": system, "count": count}
            for system, count in sorted(system_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        return {"total_scenarios": scenarios_played, "favorite_systems": favorite_systems, "longest_campaigns": []}

    def _format_statistics_response(
        self, user, start_date, end_date, session_stats, play_history_details, session_breakdown, scenario_stats
    ):
        """統計データをレスポンス形式にフォーマット"""
        return {
            "user_statistics": {
                "user_id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "total_sessions": session_stats["total_sessions"],
                "total_play_time": round(session_stats["total_play_time"] / 60, 1),  # 時間に変換
                "scenarios_played": scenario_stats["total_scenarios"],
                "gm_sessions": session_stats["gm_sessions"],
                "player_sessions": session_stats["player_sessions"],
                "date_range": {"start_date": start_date, "end_date": end_date},
            },
            "play_history": play_history_details,
            "session_statistics": session_breakdown,
            "scenario_statistics": scenario_stats,
            "export_metadata": {
                "export_date": timezone.now().isoformat(),
                "total_records": len(play_history_details),
                "date_range_applied": bool(start_date or end_date),
            },
        }

    def _export_json(self, data):
        """JSON形式でエクスポート"""
        export_data = {
            "user_statistics": data.get("user_statistics", {}),
            "play_history": data.get("play_history", []),
            "session_statistics": data.get("session_statistics", {}),
            "scenario_statistics": data.get("scenario_statistics", {}),
            "export_metadata": data.get("export_metadata", {}),
            "sessions": [
                {
                    "id": history.get("session_title", ""),
                    "title": history.get("session_title", ""),
                    "date": history.get("played_date", ""),
                    "duration_minutes": history.get("duration_minutes", 0),
                    "group": history.get("group_name", ""),
                }
                for history in data.get("play_history", [])
            ],
            "statistics": data.get("user_statistics", {}),
        }

        response = HttpResponse(json.dumps(export_data, ensure_ascii=False, indent=2), content_type="application/json")
        response["Content-Disposition"] = (
            f'attachment; filename="statistics_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
        )
        return response

    def _export_csv(self, data):
        """CSV形式でエクスポート"""
        try:
            output = StringIO()
            writer = csv.writer(output)

            # ヘッダー情報
            writer.writerow(["タブレノ - Statistics Export"])
            writer.writerow([f'User: {data["user_statistics"]["nickname"]}'])
            writer.writerow([f'Export Date: {data["export_metadata"]["export_date"]}'])
            writer.writerow([f'Total Records: {data["export_metadata"]["total_records"]}'])

            if data["user_statistics"]["date_range"]["start_date"]:
                writer.writerow(
                    [
                        f'Date Range: {data["user_statistics"]["date_range"]["start_date"]} to {data["user_statistics"]["date_range"]["end_date"] or "present"}'
                    ]
                )

            writer.writerow([])

            # プレイ履歴データ
            writer.writerow(
                [
                    "scenario_title",
                    "session_title",
                    "played_date",
                    "role",
                    "duration_minutes",
                    "game_system",
                    "group_name",
                    "notes",
                ]
            )

            for history in data["play_history"]:
                writer.writerow(
                    [
                        history.get("scenario_title", ""),
                        history.get("session_title", ""),
                        history.get("played_date", ""),
                        history.get("role", ""),
                        history.get("duration_minutes", 0),
                        history.get("game_system", ""),
                        history.get("group_name", ""),
                        history.get("notes", ""),
                    ]
                )

            response = HttpResponse(output.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="statistics_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            )
            return response
        except Exception:
            logger.exception("CSV statistics export failed")
            raise


class ExportFormatsView(APIView):
    """エクスポート形式一覧ビュー（新仕様）"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """利用可能なエクスポート形式一覧を返す"""
        formats = [
            {
                "format": "json",
                "name": "json",
                "description": "JSON形式 - プログラムでの処理や詳細分析に適しています",
                "mime_type": "application/json",
                "available": True,
            },
            {
                "format": "csv",
                "name": "csv",
                "description": "CSV形式 - Excel等の表計算ソフトで開くことができます",
                "mime_type": "text/csv",
                "available": True,
            },
        ]

        response_payload = {
            "formats": formats,
            "default_format": "json",
            "supported_parameters": {
                "format": ["json", "csv"],
                "start_date": "YYYY-MM-DD format",
                "end_date": "YYYY-MM-DD format",
            },
        }

        export_format = request.query_params.get("format")
        if export_format:
            stats_view = StatisticsExportView()
            stats_data = stats_view._collect_user_statistics(
                request.user,
                request.query_params.get("start_date"),
                request.query_params.get("end_date"),
            )
            response_payload.update(
                {
                    "user_info": {
                        "id": request.user.id,
                        "username": request.user.username,
                        "nickname": request.user.nickname or request.user.username,
                    },
                    "statistics": stats_data.get("user_statistics", {}),
                }
            )

        return Response(response_payload)
