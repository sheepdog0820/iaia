import json

from django.core.management.base import BaseCommand, CommandError

from schedules.models import SessionInvitation, TRPGSession


class Command(BaseCommand):
    help = "Output one session and its invitation statuses as JSON for AWS investigation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--session-id",
            type=int,
            required=True,
            help="ID of the session to inspect.",
        )

    def handle(self, *args, **options):
        session_id = options["session_id"]
        session = TRPGSession.objects.select_related("group").filter(pk=session_id).first()
        if session is None:
            raise CommandError(f"Session {session_id} does not exist.")

        invitations = [
            {
                "id": invitation["id"],
                "invitee_username": invitation["invitee__username"],
                "status": invitation["status"],
                "invited_role": invitation["invited_role"],
            }
            for invitation in SessionInvitation.objects.filter(session_id=session_id)
            .order_by("id")
            .values("id", "invitee__username", "status", "invited_role")
        ]
        payload = {
            "session": {
                "id": session.pk,
                "title": session.title,
                "group_id": session.group_id,
                "group_name": session.group.name if session.group else None,
            },
            "invitation_count": len(invitations),
            "invitations": invitations,
        }
        self.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
