import json
import logging
import mimetypes
from datetime import timedelta
from urllib import request

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from support.models import LineWebhookEvent, SupportMessage, SupportTicket

logger = logging.getLogger(__name__)


def _line_request(url, payload):
    token = settings.LINE_CHANNEL_ACCESS_TOKEN
    if not token:
        raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN is not configured")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=settings.LINE_API_TIMEOUT_SECONDS) as response:
        if response.status >= 300:
            raise RuntimeError(f"LINE API returned HTTP {response.status}")


def reply_to_line(reply_token, text):
    _line_request(
        "https://api.line.me/v2/bot/message/reply",
        {"replyToken": reply_token, "messages": [{"type": "text", "text": text}]},
    )


def push_to_line(user_id, text):
    _line_request(
        "https://api.line.me/v2/bot/message/push",
        {"to": user_id, "messages": [{"type": "text", "text": text}]},
    )


def resolve_ticket_and_notify(ticket):
    push_to_line(
        ticket.line_user_id,
        f"受付番号 {ticket.reference} の対応が完了しました。ご報告ありがとうございました。",
    )
    ticket.status = SupportTicket.Status.RESOLVED
    ticket.resolved_at = timezone.now()
    ticket.notification_error = ""
    ticket.save(update_fields=("status", "resolved_at", "notification_error", "updated_at"))


def fetch_line_content(message_id):
    token = settings.LINE_CHANNEL_ACCESS_TOKEN
    if not token:
        raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN is not configured")
    req = request.Request(
        f"https://api-data.line.me/v2/bot/message/{message_id}/content",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    max_bytes = settings.LINE_MAX_ATTACHMENT_BYTES
    with request.urlopen(req, timeout=settings.LINE_API_TIMEOUT_SECONDS) as response:
        declared_size = int(response.headers.get("Content-Length") or 0)
        if declared_size > max_bytes:
            raise ValueError("LINE attachment exceeds the configured size limit")
        content = response.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise ValueError("LINE attachment exceeds the configured size limit")
        return content, response.headers.get_content_type()


def _notify_admin(ticket, body, *, is_new):
    recipient = settings.LINE_SUPPORT_ADMIN_EMAIL
    if not recipient:
        return
    admin_path = f"/admin/support/supportticket/{ticket.pk}/change/"
    admin_url = f"{settings.PUBLIC_SITE_URL.rstrip('/')}{admin_path}" if settings.PUBLIC_SITE_URL else admin_path
    send_mail(
        subject=(
            f"[Tableno障害報告][{ticket.reference}] {ticket.subject}"
            if is_new
            else f"[Tableno障害報告][追記][{ticket.reference}] {ticket.subject}"
        ),
        message=(
            "LINEから新しい障害報告を受け付けました。\n\n"
            f"受付番号: {ticket.reference}\n"
            f"内容: {body}\n\n"
            f"管理画面: {admin_url}\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=False,
    )


def _open_ticket_for(user_id):
    return (
        SupportTicket.objects.filter(
            line_user_id=user_id,
            status__in=(
                SupportTicket.Status.NEW,
                SupportTicket.Status.INVESTIGATING,
                SupportTicket.Status.WAITING,
            ),
            updated_at__gte=timezone.now() - timedelta(hours=settings.LINE_TICKET_FOLLOWUP_HOURS),
        )
        .order_by("-updated_at")
        .first()
    )


def _process_message_event(event_record, payload):
    message = payload.get("message") or {}
    message_type = message.get("type")
    if message_type not in {"text", "image"} or not message.get("id"):
        event_record.status = LineWebhookEvent.Status.IGNORED
        event_record.processed_at = timezone.now()
        event_record.save(update_fields=("status", "processed_at"))
        return

    user_id = (payload.get("source") or {}).get("userId", "")
    body = (message.get("text") or "").strip() if message_type == "text" else "画像が送信されました"
    if not user_id or (message_type == "text" and not body):
        event_record.status = LineWebhookEvent.Status.IGNORED
        event_record.processed_at = timezone.now()
        event_record.save(update_fields=("status", "processed_at"))
        return

    ticket = _open_ticket_for(user_id)
    is_new = ticket is None
    if is_new:
        subject = body.replace("\n", " ")[:80]
        ticket = SupportTicket.objects.create(subject=subject, line_user_id=user_id)
    support_message = SupportMessage.objects.create(
        ticket=ticket,
        kind=SupportMessage.Kind.TEXT if message_type == "text" else SupportMessage.Kind.IMAGE,
        body=body,
        line_message_id=message["id"],
        raw_payload=message,
    )
    if message_type == "image":
        content, content_type = fetch_line_content(message["id"])
        extension = ".jpg" if content_type == "image/jpeg" else (mimetypes.guess_extension(content_type) or ".bin")
        support_message.attachment.save(f"{message['id']}{extension}", ContentFile(content), save=True)
    if not is_new:
        ticket.save(update_fields=("updated_at",))
    event_record.ticket = ticket
    event_record.status = LineWebhookEvent.Status.PROCESSED
    event_record.processed_at = timezone.now()
    event_record.save(update_fields=("ticket", "status", "processed_at"))

    errors = []
    reply_token = payload.get("replyToken")
    if reply_token:
        try:
            reply_to_line(
                reply_token,
                (
                    f"障害報告を受け付けました。受付番号は {ticket.reference} です。内容を確認後、順次対応します。"
                    if is_new
                    else f"受付番号 {ticket.reference} に内容を追加しました。"
                ),
            )
        except Exception as exc:  # External delivery failure must not roll back the ticket.
            logger.exception("LINE reply failed for %s", ticket.reference)
            errors.append(f"LINE reply: {exc}")
    try:
        _notify_admin(ticket, body, is_new=is_new)
    except Exception as exc:  # External delivery failure must not roll back the ticket.
        logger.exception("Admin notification failed for %s", ticket.reference)
        errors.append(f"Admin email: {exc}")
    if errors:
        ticket.notification_error = "\n".join(errors)
        ticket.save(update_fields=("notification_error", "updated_at"))


def process_line_event(payload):
    event_id = payload.get("webhookEventId")
    if not event_id:
        return None
    try:
        with transaction.atomic():
            event_record, created = LineWebhookEvent.objects.select_for_update().get_or_create(
                event_id=event_id,
                defaults={"raw_payload": payload},
            )
            if not created and event_record.status in {
                LineWebhookEvent.Status.PROCESSED,
                LineWebhookEvent.Status.IGNORED,
            }:
                return event_record
            if payload.get("type") != "message":
                event_record.status = LineWebhookEvent.Status.IGNORED
                event_record.processed_at = timezone.now()
                event_record.save(update_fields=("status", "processed_at"))
            else:
                _process_message_event(event_record, payload)
            return event_record
    except Exception as exc:
        LineWebhookEvent.objects.filter(event_id=event_id).update(
            status=LineWebhookEvent.Status.FAILED,
            last_error=str(exc),
        )
        raise


def queue_line_event(payload):
    event_id = payload.get("webhookEventId")
    if not event_id:
        return None
    event_record, created = LineWebhookEvent.objects.get_or_create(
        event_id=event_id,
        defaults={"raw_payload": payload},
    )
    if not created and event_record.status != LineWebhookEvent.Status.FAILED:
        return event_record
    if settings.LINE_WEBHOOK_USE_CELERY:
        from support.tasks import process_line_event_task

        process_line_event_task.delay(event_record.pk)
    else:
        process_line_event(payload)
    return event_record
