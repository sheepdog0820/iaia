"""Operational error notifications without request or exception payloads."""

import logging
from copy import copy
from datetime import datetime, timezone
from pathlib import Path
from traceback import walk_tb

from django.utils.log import AdminEmailHandler


def error_summary(record):
    request = getattr(record, "request", None)
    match = getattr(request, "resolver_match", None)
    route = getattr(match, "view_name", None) or "unresolved"
    method = getattr(request, "method", "unknown")
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
        method = "unknown"
    status = getattr(record, "status_code", None)
    if not isinstance(status, int) or not 100 <= status <= 599:
        status = "unknown"
    exception_type = record.exc_info[0].__name__ if record.exc_info and record.exc_info[0] else "none"
    subject = f"{record.levelname}: {exception_type} ({route})"
    lines = [
        f"time={datetime.fromtimestamp(record.created, timezone.utc).isoformat()}",
        f"logger={record.name}",
        f"level={record.levelname}",
        f"route={route}",
        f"method={method}",
        f"status={status}",
        f"exception_type={exception_type}",
    ]
    if record.exc_info and record.exc_info[2]:
        lines.append("stack:")
        for frame, line in walk_tb(record.exc_info[2]):
            code = frame.f_code
            lines.append(f"  {Path(code.co_filename).name}:{line} in {code.co_name}")
    return subject, "\n".join(lines)


class SafeAdminEmailHandler(AdminEmailHandler):
    def emit(self, record):
        subject, body = error_summary(record)
        self.send_mail(self.format_subject(subject), body, fail_silently=True, html_message=None)


class SafeRequestFormatter(logging.Formatter):
    def format(self, record):
        safe_record = copy(record)
        if hasattr(record, "request") or record.name == "django.request" or record.name.startswith("django.security"):
            _, safe_record.msg = error_summary(record)
            safe_record.args = ()
            safe_record.exc_info = None
            safe_record.exc_text = None
            safe_record.stack_info = None
        return super().format(safe_record)
