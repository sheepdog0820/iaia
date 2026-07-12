from django.urls import path

from support.views import line_webhook

urlpatterns = [
    path("line/webhook/", line_webhook, name="line-support-webhook"),
]
