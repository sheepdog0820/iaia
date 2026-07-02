from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from scenarios.models import Scenario
from schedules.models import DatePoll, TRPGSession

from .models import Group, GroupLink, GroupLinkShare, GroupMembership


def _is_group_admin(user, group):
    return (
        group.created_by_id == user.id or GroupMembership.objects.filter(user=user, group=group, role="admin").exists()
    )


class GroupLinkSerializer(serializers.ModelSerializer):
    source_group_name = serializers.CharField(source="source_group.name", read_only=True)
    target_group_name = serializers.CharField(source="target_group.name", read_only=True)

    class Meta:
        model = GroupLink
        fields = [
            "id",
            "source_group",
            "source_group_name",
            "target_group",
            "target_group_name",
            "status",
            "created_at",
            "responded_at",
        ]


class GroupLinkListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def _group(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id)
        if not _is_group_admin(request.user, group):
            self.permission_denied(request)
        return group

    def get(self, request, group_id):
        group = self._group(request, group_id)
        links = GroupLink.objects.filter(Q(source_group=group) | Q(target_group=group)).select_related(
            "source_group", "target_group"
        )
        return Response(GroupLinkSerializer(links, many=True).data)

    def post(self, request, group_id):
        source_group = self._group(request, group_id)
        target_group = get_object_or_404(Group, pk=request.data.get("target_group_id"))
        if source_group == target_group:
            return Response(
                {"target_group_id": "A group cannot link to itself."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        existing = GroupLink.objects.filter(
            Q(source_group=source_group, target_group=target_group)
            | Q(source_group=target_group, target_group=source_group)
        ).first()
        if existing:
            return Response(
                GroupLinkSerializer(existing).data,
                status=status.HTTP_409_CONFLICT,
            )
        link = GroupLink.objects.create(
            source_group=source_group,
            target_group=target_group,
            requested_by=request.user,
        )
        return Response(
            GroupLinkSerializer(link).data,
            status=status.HTTP_201_CREATED,
        )


class GroupLinkAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id, link_id):
        link = get_object_or_404(
            GroupLink,
            pk=link_id,
            target_group_id=group_id,
            status=GroupLink.Status.PENDING,
        )
        if not _is_group_admin(request.user, link.target_group):
            self.permission_denied(request)
        link.status = GroupLink.Status.ACCEPTED
        link.responded_by = request.user
        link.responded_at = timezone.now()
        link.save(update_fields=["status", "responded_by", "responded_at"])
        return Response(GroupLinkSerializer(link).data)


class GroupLinkDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, group_id, link_id):
        link = get_object_or_404(
            GroupLink.objects.select_related("source_group", "target_group"),
            pk=link_id,
        )
        group = get_object_or_404(Group, pk=group_id)
        if group not in {link.source_group, link.target_group}:
            raise serializers.ValidationError("Group is not part of this link.")
        if not _is_group_admin(request.user, group):
            self.permission_denied(request)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _validate_shared_resource(owner_group, resource_type, object_id):
    if resource_type == GroupLinkShare.ResourceType.SESSION:
        return TRPGSession.objects.filter(pk=object_id, group=owner_group).exists()
    if resource_type == GroupLinkShare.ResourceType.DATE_POLL:
        return DatePoll.objects.filter(pk=object_id, group=owner_group).exists()
    if resource_type == GroupLinkShare.ResourceType.SCENARIO:
        return Scenario.objects.filter(pk=object_id, sessions__group=owner_group).exists()
    return False


class GroupLinkShareView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id, link_id):
        link = get_object_or_404(
            GroupLink,
            pk=link_id,
            status=GroupLink.Status.ACCEPTED,
        )
        owner_group = get_object_or_404(Group, pk=group_id)
        if owner_group.id not in {link.source_group_id, link.target_group_id}:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not _is_group_admin(request.user, owner_group):
            self.permission_denied(request)
        resource_type = request.data.get("resource_type")
        object_id = request.data.get("object_id")
        if not _validate_shared_resource(owner_group, resource_type, object_id):
            return Response(
                {"detail": "Resource does not belong to this group."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        share, created = GroupLinkShare.objects.get_or_create(
            link=link,
            owner_group=owner_group,
            resource_type=resource_type,
            object_id=object_id,
            defaults={"created_by": request.user},
        )
        return Response(
            {
                "id": share.pk,
                "resource_type": share.resource_type,
                "object_id": share.object_id,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, group_id, link_id):
        link = get_object_or_404(GroupLink, pk=link_id)
        owner_group = get_object_or_404(Group, pk=group_id)
        if not _is_group_admin(request.user, owner_group):
            self.permission_denied(request)
        deleted, _ = GroupLinkShare.objects.filter(
            link=link,
            owner_group=owner_group,
            resource_type=request.data.get("resource_type"),
            object_id=request.data.get("object_id"),
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT if deleted else status.HTTP_404_NOT_FOUND)
