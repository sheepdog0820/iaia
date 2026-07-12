from django.contrib import admin, messages

from support.models import LineWebhookEvent, SupportMessage, SupportTicket
from support.services import resolve_ticket_and_notify


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0
    readonly_fields = ("kind", "body", "line_message_id", "attachment", "created_at")


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("reference", "subject", "source", "status", "created_at", "updated_at")
    list_filter = ("source", "status")
    search_fields = ("reference", "subject", "line_user_id", "messages__body")
    readonly_fields = ("reference", "source", "line_user_id", "notification_error", "created_at", "updated_at")
    inlines = (SupportMessageInline,)
    actions = ("resolve_and_notify",)

    @admin.action(description="対応済みにしてLINEへ通知")
    def resolve_and_notify(self, request, queryset):
        succeeded = 0
        for ticket in queryset.exclude(status=SupportTicket.Status.RESOLVED):
            try:
                resolve_ticket_and_notify(ticket)
            except Exception as exc:
                ticket.notification_error = f"LINE completion notice: {exc}"
                ticket.save(update_fields=("notification_error", "updated_at"))
                self.message_user(request, f"{ticket.reference}: LINE通知に失敗しました。", messages.ERROR)
                continue
            succeeded += 1
        if succeeded:
            self.message_user(request, f"{succeeded}件を対応済みにし、LINEへ通知しました。", messages.SUCCESS)


@admin.register(LineWebhookEvent)
class LineWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "status", "ticket", "received_at", "processed_at")
    list_filter = ("status",)
    search_fields = ("event_id", "ticket__reference")
    readonly_fields = ("event_id", "status", "raw_payload", "ticket", "last_error", "received_at", "processed_at")
