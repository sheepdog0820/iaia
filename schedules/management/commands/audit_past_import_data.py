from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q

from accounts.character_models import CharacterSheet
from accounts.models import Group, GroupMembership
from scenarios.models import Scenario
from schedules.models import SessionParticipant, TRPGSession


class Command(BaseCommand):
    help = "Audit imported past TRPG schedule data and report missing repair items."

    def add_arguments(self, parser):
        parser.add_argument(
            "--group-name",
            default="TRPGスケジュール表2026 過去データ",
            help="Imported past-data group name to audit.",
        )
        parser.add_argument("--expected-created-by", default="sheepdog1919")
        parser.add_argument("--strict", action="store_true", help="Exit with an error when issues are found.")

    def handle(self, *args, **options):
        group = self._get_group(options["group_name"])
        expected_username = options["expected_created_by"]
        sessions = TRPGSession.objects.filter(group=group).select_related("created_by", "gm", "scenario")
        session_ids = list(sessions.values_list("id", flat=True))
        scenario_ids = list(sessions.exclude(scenario__isnull=True).values_list("scenario_id", flat=True).distinct())
        scenarios = Scenario.objects.filter(id__in=scenario_ids).select_related("created_by")

        issues = []
        if group.created_by.username != expected_username:
            issues.append(f"group owner mismatch: group={group.name} created_by={group.created_by.username}")
        if not GroupMembership.objects.filter(group=group, user__username=expected_username, role="admin").exists():
            issues.append(f"group admin membership missing: user={expected_username}")

        for session in sessions.exclude(created_by__username=expected_username):
            created_by = session.created_by.username if session.created_by else "-"
            issues.append(f"session creator mismatch: id={session.id} title={session.title} created_by={created_by}")

        for scenario in scenarios.exclude(created_by__username=expected_username):
            issues.append(
                f"scenario creator mismatch: id={scenario.id} title={scenario.title} created_by={scenario.created_by.username}"
            )

        missing_sales = scenarios.filter(
            Q(public_info="") | Q(scenario_tags="") | Q(setting_location="") | Q(scenario_style="")
        )
        for scenario in missing_sales:
            missing = []
            for field in ["public_info", "scenario_tags", "setting_location", "scenario_style"]:
                if not getattr(scenario, field):
                    missing.append(field)
            issues.append(
                f'scenario sales info incomplete: id={scenario.id} title={scenario.title} missing={",".join(missing)}'
            )

        guest_aliases = SessionParticipant.objects.filter(
            session_id__in=session_ids,
            user__isnull=True,
            guest_name__in=["しぇぱ"],
        ).select_related("session")
        for participant in guest_aliases:
            issues.append(
                f"guest alias not linked: session_id={participant.session_id} title={participant.session.title} guest={participant.guest_name}"
            )

        character_unlinked = (
            SessionParticipant.objects.filter(
                session_id__in=session_ids,
                user__isnull=False,
                role="player",
                character_sheet__isnull=True,
            )
            .select_related("session", "session__scenario", "user")
            .order_by("session_id", "id")
        )
        for participant in character_unlinked:
            candidates = self._character_sheet_candidates(participant)
            if len(candidates) == 1:
                issues.append(
                    "character sheet linkable: "
                    f"session_id={participant.session_id} title={participant.session.title} "
                    f"user={participant.user.username} character_id={candidates[0].id} character={candidates[0].name}"
                )
            elif len(candidates) > 1:
                ids = ",".join(str(candidate.id) for candidate in candidates)
                issues.append(
                    "character sheet ambiguous: "
                    f"session_id={participant.session_id} title={participant.session.title} "
                    f"user={participant.user.username} candidates={ids}"
                )

        participant_counts = (
            SessionParticipant.objects.filter(session_id__in=session_ids)
            .values("session_id")
            .annotate(
                gm_count=Count("id", filter=Q(role="gm")),
                player_count=Count("id", filter=Q(role="player")),
            )
        )
        counts_by_session = {row["session_id"]: row for row in participant_counts}
        for session in sessions:
            counts = counts_by_session.get(session.id, {"gm_count": 0, "player_count": 0})
            gm_participant = SessionParticipant.objects.filter(session=session, user=session.gm, role="gm").exists()
            if not gm_participant:
                issues.append(
                    f"gm participant missing: session_id={session.id} title={session.title} gm={session.gm.username}"
                )
            if counts["player_count"] == 0:
                issues.append(f"no player participants: session_id={session.id} title={session.title}")

        self.stdout.write(f"group: id={group.id} name={group.name}")
        self.stdout.write(f"sessions={sessions.count()} scenarios={scenarios.count()} issues={len(issues)}")
        for issue in issues:
            self.stdout.write(self.style.WARNING(issue))

        if issues and options["strict"]:
            raise CommandError(f"past import audit failed: issues={len(issues)}")
        self.stdout.write(self.style.SUCCESS("past import audit complete"))

    def _get_group(self, group_name):
        matches = list(Group.objects.filter(name=group_name).order_by("id"))
        if not matches:
            raise CommandError(f"group not found: {group_name}")
        if len(matches) > 1:
            ids = ", ".join(str(group.id) for group in matches)
            raise CommandError(f"group name is not unique: {group_name} ids={ids}")
        return matches[0]

    def _character_sheet_candidates(self, participant):
        if not participant.user_id:
            return []

        base_query = CharacterSheet.objects.filter(user=participant.user, is_active=True)
        if participant.character_name:
            by_name = list(base_query.filter(name=participant.character_name).order_by("id"))
            if len(by_name) == 1:
                return by_name
            if len(by_name) > 1:
                return by_name

        scenario = participant.session.scenario
        if not scenario:
            return []

        return list(
            base_query.filter(Q(source_scenario=scenario) | Q(source_scenario_title=scenario.title)).order_by("id")
        )
