from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from django.db.models import F, Q

from accounts.models import GroupLink, GroupLinkShare, GroupMembership
from .models import SessionTemplate, SessionTemplateImage
from .serializers import SessionTemplateImageSerializer, SessionTemplateSerializer


class SessionTemplateViewSet(viewsets.ModelViewSet):
    queryset = SessionTemplate.objects.none()
    serializer_class = SessionTemplateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        group_ids = GroupMembership.objects.filter(
            user=self.request.user
        ).values_list('group_id', flat=True)
        shared_template_ids = GroupLinkShare.objects.filter(
            resource_type=GroupLinkShare.ResourceType.SESSION_TEMPLATE,
            link__status=GroupLink.Status.ACCEPTED,
        ).filter(
            Q(owner_group_id=F('link__source_group_id'), link__target_group_id__in=group_ids)
            | Q(owner_group_id=F('link__target_group_id'), link__source_group_id__in=group_ids)
        ).values_list('object_id', flat=True)
        return (
            SessionTemplate.objects.filter(
                Q(owner=self.request.user) | Q(id__in=shared_template_ids)
            )
            .select_related('group', 'scenario')
            .prefetch_related('handout_templates', 'image_templates')
            .order_by('name', 'id')
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def update(self, request, *args, **kwargs):
        if self.get_object().owner_id != request.user.id:
            return Response(
                {'detail': 'Shared templates are read-only.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().owner_id != request.user.id:
            return Response(
                {'detail': 'Shared templates are read-only.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get', 'post'])
    def images(self, request, pk=None):
        template = self.get_object()

        if request.method.lower() == 'get':
            images = template.image_templates.order_by('order', 'id')
            serializer = SessionTemplateImageSerializer(
                images,
                many=True,
                context={'request': request},
            )
            return Response(serializer.data)

        if template.owner_id != request.user.id:
            return Response(
                {'detail': 'Shared templates are read-only.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        files = request.FILES.getlist('images') or []
        single_file = request.FILES.get('image')
        if single_file:
            files.append(single_file)

        if not files:
            return Response(
                {'error': 'images is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload_serializers = []
        for image_file in files[:10]:
            serializer = SessionTemplateImageSerializer(
                data={
                    'image': image_file,
                    'title': image_file.name,
                },
                context={'request': request},
            )
            serializer.is_valid(raise_exception=True)
            upload_serializers.append(serializer)

        created_images = [
            serializer.save(session_template=template)
            for serializer in upload_serializers
        ]

        serializer = SessionTemplateImageSerializer(
            created_images,
            many=True,
            context={'request': request},
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[
            OpenApiParameter('image_id', OpenApiTypes.INT, OpenApiParameter.PATH),
        ],
    )
    @action(detail=True, methods=['delete'], url_path=r'images/(?P<image_id>[^/.]+)')
    def delete_image(self, request, pk=None, image_id=None):
        template = self.get_object()
        image = template.image_templates.filter(id=image_id).first()
        if image is None:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)

        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
