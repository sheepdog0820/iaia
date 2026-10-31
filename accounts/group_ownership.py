"""Consent-based group ownership; group locks precede ordered user locks."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import Group, GroupMembership, GroupOwnershipTransfer


class OwnershipTransferError(ValueError):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.status = status


def _identifier(value):
    if type(value) is not int or not 0 < value <= 9223372036854775807:
        raise OwnershipTransferError("invalid_id", "対象のIDは正の整数で指定してください。")
    return value


def _locked_group(group_id):
    group = Group.objects.select_for_update().filter(pk=_identifier(group_id)).first()
    if group is None:
        raise OwnershipTransferError("not_found", "グループが見つかりません。", 404)
    return group


def _locked_users(group, actor, *extra_ids):
    actor_id = getattr(actor, "pk", None)
    if actor_id is None:
        raise OwnershipTransferError("unauthenticated", "ログインしてください。", 403)
    ids = sorted({_identifier(actor_id), group.owner_id, *extra_ids})
    users = {user.pk: user for user in get_user_model().objects.select_for_update().filter(pk__in=ids).order_by("pk")}
    if actor_id not in users or not users[actor_id].is_active:
        raise OwnershipTransferError("inactive_actor", "有効なアカウントでログインしてください。", 403)
    return users


def _require_owner(group, actor):
    if group.owner_id != actor.pk:
        raise OwnershipTransferError("not_owner", "所有権の申請・取消は現在の所有者だけが行えます。", 403)


def _pending(group, request_id, *, target_id=None):
    pending = GroupOwnershipTransfer.objects.select_for_update().filter(group=group, pk=_identifier(request_id))
    if target_id is not None:
        # Non-targets receive the same response for real and unknown request IDs.
        pending = pending.filter(target_id=target_id)
    request = pending.first()
    if request is None:
        raise OwnershipTransferError("not_found", "この申請は終了しているか、見つかりません。", 404)
    if request.requested_by_id != group.owner_id:
        raise OwnershipTransferError("changed", "所有者が変わっています。画面を再読み込みしてください。", 409)
    return request


@transaction.atomic
def start_transfer(group_id, actor, target_user_id):
    target_user_id = _identifier(target_user_id)
    group = _locked_group(group_id)
    users = _locked_users(group, actor, target_user_id)
    _require_owner(group, actor)
    target = users.get(target_user_id)
    if (
        target is None
        or not target.is_active
        or target.pk == group.owner_id
        or not GroupMembership.objects.filter(group=group, user_id=target.pk).exists()
    ):
        raise OwnershipTransferError("invalid_target", "自分以外の有効な登録メンバーを指定してください。")
    now = timezone.now()
    previous = GroupOwnershipTransfer.objects.select_for_update().filter(group=group).first()
    if previous is not None:
        if previous.expires_at > now and previous.requested_by_id == group.owner_id:
            raise OwnershipTransferError(
                "pending_exists", "申請中です。先の申請を取り消してから指定してください。", 409
            )
        previous.delete()
    return GroupOwnershipTransfer.objects.create(
        group=group, requested_by=users[actor.pk], target=target, created_at=now, expires_at=now + timedelta(days=7)
    )


@transaction.atomic
def accept_transfer(group_id, actor, request_id):
    group = _locked_group(group_id)
    users = _locked_users(group, actor)
    request = _pending(group, request_id, target_id=actor.pk)
    if request.expires_at <= timezone.now():
        raise OwnershipTransferError("expired", "申請の有効期限が切れています。所有者に再申請を依頼してください。", 410)
    membership = GroupMembership.objects.select_for_update().filter(group=group, user_id=request.target_id).first()
    if membership is None or not users[request.target_id].is_active:
        raise OwnershipTransferError(
            "invalid_target", "対象者の所属・アカウント状態が変わったため移譲できません。", 409
        )
    if group.owner_id not in users or not users[group.owner_id].is_active:
        raise OwnershipTransferError("invalid_owner", "現在の所有者の状態を確認できないため移譲できません。", 409)
    membership.role = "admin"
    membership.save(update_fields=["role"])
    GroupMembership.objects.update_or_create(group=group, user_id=group.owner_id, defaults={"role": "admin"})
    group.owner = users[request.target_id]
    group.save(update_fields=["owner", "updated_at"])
    request.delete()
    return group


@transaction.atomic
def cancel_transfer(group_id, actor, request_id):
    group = _locked_group(group_id)
    _locked_users(group, actor)
    _require_owner(group, actor)
    _pending(group, request_id).delete()


@transaction.atomic
def decline_transfer(group_id, actor, request_id):
    group = _locked_group(group_id)
    _locked_users(group, actor)
    request = _pending(group, request_id, target_id=actor.pk)
    request.delete()


def pending_transfer(group_id, actor):
    group = Group.objects.filter(pk=_identifier(group_id)).first()
    if group is None or not get_user_model().objects.filter(pk=getattr(actor, "pk", None), is_active=True).exists():
        raise OwnershipTransferError("not_found", "グループが見つかりません。", 404)
    request = GroupOwnershipTransfer.objects.select_related("target").filter(group=group).first()
    if request is None or actor.pk not in (group.owner_id, request.target_id):
        return None
    if actor.pk != group.owner_id and not GroupMembership.objects.filter(group=group, user=actor).exists():
        return None
    return request


def transfer_candidates(group_id, actor):
    group = Group.objects.filter(pk=_identifier(group_id), owner_id=getattr(actor, "pk", None)).first()
    if group is None:
        return []
    users = group.members.filter(is_active=True).exclude(pk=group.owner_id).order_by("pk")
    return [{"id": user.pk, "name": user.nickname or user.username, "username": user.username} for user in users]


def _deletion_group_ids(user_id):
    return set(
        Group.objects.filter(Q(owner_id=user_id) | Q(created_by_id=user_id) | Q(groupmembership__user_id=user_id))
        .values_list("pk", flat=True)
        .distinct()
    )


def _check_not_owner(user_id):
    if Group.objects.filter(owner_id=user_id).exists():
        raise OwnershipTransferError(
            "owns_groups",
            "所有しているグループがあります。先に所有権を移譲するか、グループを明示的に削除してください。",
        )


def lock_account_deletion_groups(user_id):
    """Called in deletion's transaction, before its subscription and user locks."""
    ids = _deletion_group_ids(_identifier(user_id))
    list(Group.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
    _check_not_owner(user_id)
    return ids


def verify_account_deletion_groups(user_id, locked_ids):
    # The user row is now locked, preventing new FK references. A newly joined
    # or created group missing from the earlier snapshot requires a fresh try.
    if _deletion_group_ids(user_id) - locked_ids:
        raise OwnershipTransferError(
            "changed", "グループの状態が変わりました。画面を再読み込みしてから削除してください。", 409
        )
    _check_not_owner(user_id)
