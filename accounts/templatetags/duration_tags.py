from django import template

from schedules.duration import format_duration_hours, minutes_to_hours

register = template.Library()


@register.filter
def duration_hours(minutes):
    return format_duration_hours(minutes)


@register.filter
def duration_hour_value(minutes):
    return minutes_to_hours(minutes) or ""
