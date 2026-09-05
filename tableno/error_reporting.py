"""Operational error notifications without request or exception payloads."""

from datetime import datetime, timezone
from pathlib import Path
from traceback import walk_tb

from django.utils.log import AdminEmailHandler


class SafeAdminEmailHandler(AdminEmailHandler):
    def emit(self, record):
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
        subject = self.format_subject(f"{record.levelname}: {exception_type} ({route})")
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
        self.send_mail(subject, "\n".join(lines), fail_silently=True, html_message=None)
