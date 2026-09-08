from django.urls import path

from support.attachment_views import download_attachment
from support.views import line_webhook

urlpatterns = [
    path("attachments/<int:pk>/download/", download_attachment, name="support-attachment-download"),
    path("line/webhook/", line_webhook, name="line-support-webhook"),
]
