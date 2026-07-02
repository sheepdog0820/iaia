from django.contrib import admin

from .models import HandoutInfo, JapaneseHoliday, SessionParticipant, SessionReward, TRPGSession


class SessionParticipantInline(admin.TabularInline):
    model = SessionParticipant
    extra = 1


class HandoutInfoInline(admin.TabularInline):
    model = HandoutInfo
    extra = 0
    fields = ("code", "name", "title", "participant", "is_secret", "handout_number", "assigned_player_slot", "order")
    readonly_fields = ("created_at",)


@admin.register(TRPGSession)
class TRPGSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "gm", "group", "status", "visibility")
    list_filter = ("status", "visibility", "date", "created_at")
    search_fields = ("title", "description", "gm__username", "group__name")
    date_hierarchy = "date"
    ordering = ("-date",)

    inlines = [SessionParticipantInline, HandoutInfoInline]

    fieldsets = (
        ("基本情報", {"fields": ("title", "description", "date", "location")}),
        ("参加者情報", {"fields": ("gm", "group")}),
        ("設定", {"fields": ("status", "visibility", "youtube_url", "duration_minutes", "actual_duration_minutes")}),
    )


@admin.register(SessionParticipant)
class SessionParticipantAdmin(admin.ModelAdmin):
    list_display = ("session", "user", "role", "character_name")
    list_filter = ("role",)
    search_fields = ("session__title", "user__username", "character_name")


@admin.register(HandoutInfo)
class HandoutInfoAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "title", "session", "participant", "is_secret", "order", "created_at")
    list_filter = ("is_secret", "created_at")
    search_fields = ("code", "name", "title", "content", "session__title", "participant__user__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(JapaneseHoliday)
class JapaneseHolidayAdmin(admin.ModelAdmin):
    list_display = ("date", "name", "source", "fetched_at", "updated_at")
    list_filter = ("source", "fetched_at")
    search_fields = ("name", "source_url")
    date_hierarchy = "date"
    readonly_fields = ("created_at", "updated_at")


@admin.register(SessionReward)
class SessionRewardAdmin(admin.ModelAdmin):
    list_display = (
        "session",
        "participant",
        "experience_points",
        "created_by",
        "applied_growth_record",
        "applied_at",
        "updated_at",
    )
    list_filter = ("applied_at", "created_at")
    search_fields = (
        "participant__session__title",
        "participant__user__username",
        "participant__guest_name",
        "special_rewards",
        "notes",
    )
    readonly_fields = ("created_at", "updated_at", "applied_at")

    @admin.display(description="session")
    def session(self, obj):
        return obj.participant.session
