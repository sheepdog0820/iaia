from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from accounts.character_models import CharacterSheet
from accounts.models import Group, GroupMembership
from schedules import session_permissions
from schedules.models import SessionParticipant, SessionParticipantRole, TRPGSession


class Command(BaseCommand):
    help = "Repair ownership and participant links for imported past TRPG schedule data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--group-name",
            default="TRPGスケジュール表2026 過去データ",
            help="Imported past-data group name to repair.",
        )
        parser.add_argument(
            "--created-by",
            default="sheepdog1919",
            help="Username to assign as group/session/scenario creator.",
        )
        parser.add_argument(
            "--guest-alias",
            action="append",
            default=["しぇぱ"],
            help="Guest display name to link to --created-by. Can be specified multiple times.",
        )
        parser.add_argument(
            "--no-ensure-gm-participants",
            action="store_true",
            help="Do not create/update SessionParticipant rows for each session GM.",
        )
        parser.add_argument(
            "--no-link-character-sheets",
            action="store_true",
            help="Do not link participant rows to matching local character sheets.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Show changes without writing to DB.")

    def handle(self, *args, **options):
        owner = self._get_user(options["created_by"])
        group = self._get_group(options["group_name"])
        guest_aliases = {alias.strip() for alias in options["guest_alias"] if alias and alias.strip()}

        stats = {
            "groups_updated": 0,
            "memberships_created": 0,
            "memberships_updated": 0,
            "sessions_updated": 0,
            "scenarios_updated": 0,
            "guests_linked": 0,
            "guests_skipped_duplicate": 0,
            "gm_participants_created": 0,
            "gm_participants_updated": 0,
            "character_sheets_linked": 0,
            "character_sheets_skipped_no_candidate": 0,
            "character_sheets_skipped_ambiguous": 0,
        }

        with transaction.atomic():
            if group.created_by_id != owner.id:
                stats["groups_updated"] += 1
                self.stdout.write(f"group owner: {group.name} -> {owner.username}")
                if not options["dry_run"]:
                    group.created_by = owner
                    group.save(update_fields=["created_by"])

            membership = GroupMembership.objects.filter(group=group, user=owner).first()
            if membership is None:
                stats["memberships_created"] += 1
                self.stdout.write(f"group admin membership create: {owner.username}")
                if not options["dry_run"]:
                    GroupMembership.objects.create(group=group, user=owner, role="admin")
            elif membership.role != "admin":
                stats["memberships_updated"] += 1
                self.stdout.write(f"group admin membership update: {owner.username}")
                if not options["dry_run"]:
                    membership.role = "admin"
                    membership.save(update_fields=["role"])

            sessions = TRPGSession.objects.filter(group=group).select_related("scenario", "gm")
            session_ids = list(sessions.values_list("id", flat=True))
            for session in sessions:
                if session.created_by_id != owner.id:
                    stats["sessions_updated"] += 1
                    self.stdout.write(f"session creator: #{session.id} {session.title} -> {owner.username}")
                    if not options["dry_run"]:
                        session.created_by = owner
                        session.save(update_fields=["created_by"])
                if session.scenario and session.scenario.created_by_id != owner.id:
                    stats["scenarios_updated"] += 1
                    self.stdout.write(
                        f"scenario creator: #{session.scenario_id} {session.scenario.title} -> {owner.username}"
                    )
                    if not options["dry_run"]:
                        session.scenario.created_by = owner
                        session.scenario.save(update_fields=["created_by"])

            if guest_aliases:
                guests = SessionParticipant.objects.filter(
                    session_id__in=session_ids,
                    user__isnull=True,
                    guest_name__in=guest_aliases,
                    participant_roles__role=SessionParticipantRole.Role.PLAYER,
                ).select_related("session")
                for participant in guests:
                    duplicate_exists = (
                        SessionParticipant.objects.filter(
                            session=participant.session,
                            user=owner,
                        )
                        .exclude(pk=participant.pk)
                        .exists()
                    )
                    if duplicate_exists:
                        stats["guests_skipped_duplicate"] += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"guest link skipped duplicate: session=#{participant.session_id} guest={participant.guest_name}"
                            )
                        )
                        continue
                    stats["guests_linked"] += 1
                    self.stdout.write(
                        f"guest link: session=#{participant.session_id} {participant.guest_name} -> {owner.username}"
                    )
                    if not options["dry_run"]:
                        participant.user = owner
                        participant.guest_name = ""
                        participant.save(update_fields=["user", "guest_name"])

            if not options["no_ensure_gm_participants"]:
                for session in sessions:
                    if not session.gm_id:
                        self.stdout.write(f"gm participant skipped: session=#{session.id} gm is not set")
                        continue
                    participant = SessionParticipant.objects.filter(session=session, user=session.gm).first()
                    if participant is None:
                        stats["gm_participants_created"] += 1
                        self.stdout.write(f"gm participant create: session=#{session.id} gm={session.gm.username}")
                        if not options["dry_run"]:
                            session_permissions.assign_session_gm(session, session.gm, granted_by=owner)
                    elif SessionParticipantRole.Role.GM.value not in session_permissions.get_participant_role_values(participant):
                        stats["gm_participants_updated"] += 1
                        self.stdout.write(f"gm participant role update: session=#{session.id} gm={session.gm.username}")
                        if not options["dry_run"]:
                            session_permissions.assign_session_gm(session, session.gm, granted_by=owner)

            if not options["no_link_character_sheets"]:
                participants = (
                    SessionParticipant.objects.filter(
                        session_id__in=session_ids,
                        user__isnull=False,
                        participant_roles__role=SessionParticipantRole.Role.PLAYER,
                        character_sheet__isnull=True,
                    )
                    .select_related("session", "session__scenario", "user")
                    .order_by("session_id", "id")
                )
                for participant in participants:
                    candidates = self._character_sheet_candidates(participant)
                    if not candidates:
                        stats["character_sheets_skipped_no_candidate"] += 1
                        self.stdout.write(
                            self.style.WARNING(
                                "character sheet skipped no candidate: "
                                f"session=#{participant.session_id} user={participant.user.username} "
                                f'character_name={participant.character_name or "-"}'
                            )
                        )
                        continue
                    if len(candidates) > 1:
                        stats["character_sheets_skipped_ambiguous"] += 1
                        ids = ",".join(str(candidate.id) for candidate in candidates)
                        self.stdout.write(
                            self.style.WARNING(
                                "character sheet skipped ambiguous: "
                                f"session=#{participant.session_id} user={participant.user.username} "
                                f'character_name={participant.character_name or "-"} candidates={ids}'
                            )
                        )
                        continue

                    character = candidates[0]
                    stats["character_sheets_linked"] += 1
                    self.stdout.write(
                        "character sheet link: "
                        f"session=#{participant.session_id} user={participant.user.username} "
                        f"participant=#{participant.id} -> character=#{character.id} {character.name}"
                    )
                    if not options["dry_run"]:
                        participant.character_sheet = character
                        participant.character_name = character.name
                        participant.save(update_fields=["character_sheet", "character_name"])

            if options["dry_run"]:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                "past import repair complete: " + ", ".join(f"{key}={value}" for key, value in stats.items())
            )
        )

    def _get_user(self, username):
        User = get_user_model()
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"user not found: {username}") from exc

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
