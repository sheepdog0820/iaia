"""Operational error notifications without request or exception payloads."""

import logging
from copy import copy
from datetime import datetime, timezone
from pathlib import Path
from traceback import walk_tb

from django.utils.log import AdminEmailHandler


def is_sdk_logger(name):
    return isinstance(name, str) and name.partition(".")[0] in {"botocore", "boto3"}


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


def sdk_error_summary(record):
    safe_record = copy(record)
    safe_record.__dict__.pop("request", None)
    safe_record.__dict__.pop("status_code", None)
    return error_summary(safe_record)


def _sentry_sdk_record(hint):
    record = (hint or {}).get("log_record")
    return record if isinstance(record, logging.LogRecord) and is_sdk_logger(record.name) else None


def _sentry_sdk_message(record):
    return sdk_error_summary(record)[1] if record is not None else "AWS SDK diagnostic payload omitted"


def safe_sentry_event(event, hint):
    record = _sentry_sdk_record(hint)
    name = record.name if record is not None else event.get("logger")
    if not is_sdk_logger(name):
        return event
    safe = {
        key: event[key]
        for key in ("event_id", "timestamp", "level", "platform", "release", "environment")
        if key in event
    }
    safe["logger"] = name
    safe["logentry"] = {"message": "AWS SDK diagnostic", "formatted": _sentry_sdk_message(record)}
    safe["fingerprint"] = ["aws-sdk", name, sdk_error_summary(record)[0] if record is not None else "unknown"]
    return safe


def safe_sentry_breadcrumb(breadcrumb, hint):
    record = _sentry_sdk_record(hint)
    name = record.name if record is not None else breadcrumb.get("category")
    if not is_sdk_logger(name):
        return breadcrumb
    safe = {key: breadcrumb[key] for key in ("type", "level", "timestamp") if key in breadcrumb}
    safe["category"] = name
    safe["message"] = _sentry_sdk_message(record)
    return safe


def safe_sentry_log(log, hint):
    attributes = log.get("attributes") or {}
    if not is_sdk_logger(attributes.get("logger.name")):
        return log
    safe = {
        key: log[key]
        for key in ("severity_text", "severity_number", "time_unix_nano", "trace_id", "span_id")
        if key in log
    }
    safe["body"] = "AWS SDK diagnostic payload omitted"
    safe["attributes"] = {
        key: attributes[key] for key in ("logger.name", "code.function.name", "code.line.number") if key in attributes
    }
    return safe


class SafeAdminEmailHandler(AdminEmailHandler):
    def emit(self, record):
        subject, body = error_summary(record)
        self.send_mail(self.format_subject(subject), body, fail_silently=True, html_message=None)


class SafeRequestFormatter(logging.Formatter):
    def format(self, record):
        safe_record = copy(record)
        if (
            hasattr(record, "request")
            or record.name == "django.request"
            or record.name.startswith("django.security")
            or is_sdk_logger(record.name)
        ):
            _, safe_record.msg = sdk_error_summary(record) if is_sdk_logger(record.name) else error_summary(record)
            safe_record.args = ()
            safe_record.exc_info = None
            safe_record.exc_text = None
            safe_record.stack_info = None
        return super().format(safe_record)
