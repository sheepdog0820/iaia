from .session_permissions import initialize_created_session_permissions
from .template_services import clone_scenario_handouts_to_session

SESSION_CREATED = "session_created"


def save_session(serializer, user, *, as_gm):
    gm = user if as_gm else None
    session = serializer.save(created_by=user, gm=gm)
    initialize_created_session_permissions(session, created_by=user, gm=gm)
    clone_scenario_handouts_to_session(session.scenario, session)
    return session


def queue_session_creation_integrations(session, *, discord=True, google_calendar=True):
    from .tasks import queue_discord_event, schedule_session_google_syncs

    if discord:
        queue_discord_event(
            session.group_id,
            SESSION_CREATED,
            {"content": f"Session created: {session.title}"},
            f"session-created:{session.pk}",
        )
    if google_calendar:
        schedule_session_google_syncs(session)
