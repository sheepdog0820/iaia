from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone

from schedules.models import HandoutNotification
from schedules.notifications import FriendNotificationService

from .models import CustomUser, Friend, FriendRequest

FRIEND_REQUEST_COOLDOWN = timedelta(hours=24)


class FriendRequestError(Exception):
    def __init__(self, message, *, status_code=400, retry_after=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.retry_after = retry_after


def publicly_searchable_users():
    return CustomUser.objects.filter(
        is_active=True,
        trpg_introduction_sheet__visibility="public",
    )


def friend_candidates(user, query):
    query = (query or "").strip()
    if len(query) < 2:
        return CustomUser.objects.none()

    now = timezone.now()
    cutoff = now - FRIEND_REQUEST_COOLDOWN
    friend_ids = set()
    for user_id, friend_id in Friend.objects.filter(Q(user=user) | Q(friend=user)).values_list("user_id", "friend_id"):
        friend_ids.add(friend_id if user_id == user.id else user_id)
    related_requests = FriendRequest.objects.filter(Q(sender=user) | Q(recipient=user))
    unavailable_requests = related_requests.filter(
        Q(status=FriendRequest.Status.PENDING)
        | Q(
            status__in=[FriendRequest.Status.DECLINED, FriendRequest.Status.CANCELLED],
            responded_at__gte=cutoff,
        )
    )
    unavailable_ids = set()
    for sender_id, recipient_id in unavailable_requests.values_list("sender_id", "recipient_id"):
        unavailable_ids.add(recipient_id if sender_id == user.id else sender_id)

    return (
        publicly_searchable_users()
        .filter(Q(username__icontains=query) | Q(nickname__icontains=query))
        .exclude(id=user.id)
        .exclude(id__in=friend_ids)
        .exclude(id__in=unavailable_ids)
        .annotate(
            exact_username_rank=Case(
                When(username__iexact=query, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("exact_username_rank", "username", "id")[:20]
    )


def _pair_filter(first_user, second_user):
    return Q(sender=first_user, recipient=second_user) | Q(sender=second_user, recipient=first_user)


def _mark_request_notification_read(friend_request):
    HandoutNotification.objects.filter(
        recipient=friend_request.recipient,
        notification_type="friend_request",
        metadata__friend_request_id=friend_request.id,
    ).update(is_read=True, read_at=timezone.now())


def _accept_locked(friend_request, accepter):
    if friend_request.status != FriendRequest.Status.PENDING:
        raise FriendRequestError("このフレンドリクエストは既に処理されています。")
    if friend_request.recipient_id != accepter.id:
        raise FriendRequestError("フレンドリクエストが見つかりません。", status_code=404)

    Friend.objects.get_or_create(user=friend_request.sender, friend=friend_request.recipient)
    Friend.objects.get_or_create(user=friend_request.recipient, friend=friend_request.sender)
    friend_request.status = FriendRequest.Status.ACCEPTED
    friend_request.responded_at = timezone.now()
    friend_request.save(update_fields=["status", "responded_at", "updated_at"])
    _mark_request_notification_read(friend_request)
    return friend_request


def create_friend_request(sender, recipient):
    if sender.id == recipient.id:
        raise FriendRequestError("自分自身にはフレンドリクエストを送れません。")

    notification_type = None

    with transaction.atomic():
        recipient = publicly_searchable_users().select_for_update().filter(id=recipient.id).first()
        if recipient is None:
            raise FriendRequestError("ユーザーが見つかりません。", status_code=404)

        pair_key = FriendRequest.make_pair_key(sender.id, recipient.id)
        if Friend.objects.filter(Q(user=sender, friend=recipient) | Q(user=recipient, friend=sender)).exists():
            raise FriendRequestError("既にフレンドです。")

        pending = (
            FriendRequest.objects.select_for_update()
            .filter(pair_key=pair_key, status=FriendRequest.Status.PENDING)
            .first()
        )
        if pending:
            if pending.sender_id == sender.id:
                raise FriendRequestError("既にフレンドリクエストを送信しています。")
            friend_request = _accept_locked(pending, sender)
            notification_type = "accepted"
            created = False
        else:
            cooldown_request = (
                FriendRequest.objects.filter(_pair_filter(sender, recipient))
                .filter(
                    status__in=[FriendRequest.Status.DECLINED, FriendRequest.Status.CANCELLED],
                    responded_at__gte=timezone.now() - FRIEND_REQUEST_COOLDOWN,
                )
                .order_by("-responded_at")
                .first()
            )
            if cooldown_request:
                retry_after = cooldown_request.responded_at + FRIEND_REQUEST_COOLDOWN
                raise FriendRequestError(
                    "再申請できるまで時間をおいてください。",
                    status_code=429,
                    retry_after=retry_after,
                )

            try:
                with transaction.atomic():
                    friend_request = FriendRequest.objects.create(sender=sender, recipient=recipient)
                notification_type = "request"
                created = True
            except IntegrityError:
                pending = FriendRequest.objects.select_for_update().get(
                    pair_key=pair_key,
                    status=FriendRequest.Status.PENDING,
                )
                if pending.sender_id == sender.id:
                    raise FriendRequestError("既にフレンドリクエストを送信しています。")
                friend_request = _accept_locked(pending, sender)
                notification_type = "accepted"
                created = False

    notification_service = FriendNotificationService()
    if notification_type == "request":
        notification_service.send_friend_request_notification(
            sender=sender,
            recipient=recipient,
            friend_request=friend_request,
        )
    else:
        notification_service.send_friend_request_accepted_notification(
            accepter=sender,
            original_sender=friend_request.sender,
            friend_request=friend_request,
        )
    return friend_request, created


def accept_friend_request(friend_request_id, recipient):
    with transaction.atomic():
        try:
            friend_request = (
                FriendRequest.objects.select_for_update()
                .select_related("sender", "recipient")
                .get(
                    id=friend_request_id,
                    recipient=recipient,
                )
            )
        except FriendRequest.DoesNotExist as exc:
            raise FriendRequestError("フレンドリクエストが見つかりません。", status_code=404) from exc
        friend_request = _accept_locked(friend_request, recipient)

    FriendNotificationService().send_friend_request_accepted_notification(
        accepter=recipient,
        original_sender=friend_request.sender,
        friend_request=friend_request,
    )
    return friend_request


def decline_friend_request(friend_request_id, recipient):
    with transaction.atomic():
        try:
            friend_request = FriendRequest.objects.select_for_update().get(
                id=friend_request_id,
                recipient=recipient,
            )
        except FriendRequest.DoesNotExist as exc:
            raise FriendRequestError("フレンドリクエストが見つかりません。", status_code=404) from exc
        if friend_request.status != FriendRequest.Status.PENDING:
            raise FriendRequestError("このフレンドリクエストは既に処理されています。")
        friend_request.status = FriendRequest.Status.DECLINED
        friend_request.responded_at = timezone.now()
        friend_request.save(update_fields=["status", "responded_at", "updated_at"])
        _mark_request_notification_read(friend_request)
    return friend_request


def cancel_friend_request(friend_request_id, sender):
    with transaction.atomic():
        try:
            friend_request = FriendRequest.objects.select_for_update().get(
                id=friend_request_id,
                sender=sender,
            )
        except FriendRequest.DoesNotExist as exc:
            raise FriendRequestError("フレンドリクエストが見つかりません。", status_code=404) from exc
        if friend_request.status != FriendRequest.Status.PENDING:
            raise FriendRequestError("このフレンドリクエストは既に処理されています。")
        friend_request.status = FriendRequest.Status.CANCELLED
        friend_request.responded_at = timezone.now()
        friend_request.save(update_fields=["status", "responded_at", "updated_at"])
        _mark_request_notification_read(friend_request)
    return friend_request
