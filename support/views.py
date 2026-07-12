import base64
import hashlib
import hmac
import json

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt

from support.services import queue_line_event


def _valid_signature(body, signature):
    secret = settings.LINE_CHANNEL_SECRET
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, signature)


@csrf_exempt
def line_webhook(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not _valid_signature(request.body, request.headers.get("X-Line-Signature", "")):
        return HttpResponseBadRequest("invalid signature")
    try:
        payload = json.loads(request.body)
    except (TypeError, ValueError):
        return HttpResponseBadRequest("invalid json")
    events = payload.get("events")
    if not isinstance(events, list):
        return HttpResponseBadRequest("invalid events")
    for event in events:
        queue_line_event(event)
    return HttpResponse(status=200)
