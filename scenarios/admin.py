from django.contrib import admin

from .models import (
    PlayHistory,
    Scenario,
    ScenarioHandout,
    ScenarioHandoutRecommendedSkill,
    ScenarioImage,
    ScenarioNote,
    ScenarioRecommendedSkill,
)


class ScenarioNoteInline(admin.TabularInline):
    model = ScenarioNote
    extra = 0
    readonly_fields = ("created_at", "updated_at")


class PlayHistoryInline(admin.TabularInline):
    model = PlayHistory
    extra = 0
    readonly_fields = ("created_at",)


class ScenarioImageInline(admin.TabularInline):
    model = ScenarioImage
    extra = 0
    readonly_fields = ("created_at", "updated_at")


class ScenarioRecommendedSkillInline(admin.TabularInline):
    model = ScenarioRecommendedSkill
    extra = 0
    fields = ("name", "level", "description", "order")


class ScenarioHandoutInline(admin.TabularInline):
    model = ScenarioHandout
    extra = 0
    fields = ("code", "name", "title", "is_secret", "handout_number", "assigned_player_slot", "order")


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "game_system", "player_count", "estimated_time", "created_by")
    list_filter = ("game_system", "player_count", "created_at")
    search_fields = ("title", "author", "summary")
    ordering = ("title",)

    inlines = [
        ScenarioRecommendedSkillInline,
        ScenarioHandoutInline,
        ScenarioImageInline,
        ScenarioNoteInline,
        PlayHistoryInline,
    ]

    fieldsets = (
        ("基本情報", {"fields": ("title", "author", "game_system")}),
        ("詳細", {"fields": ("summary", "recommended_skills", "player_count", "estimated_time")}),
    )


@admin.register(ScenarioNote)
class ScenarioNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "scenario", "user", "is_private", "created_at")
    list_filter = ("is_private", "created_at")
    search_fields = ("title", "content", "scenario__title", "user__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PlayHistory)
class PlayHistoryAdmin(admin.ModelAdmin):
    list_display = ("scenario", "user", "role", "played_date", "session")
    list_filter = ("role", "played_date")
    search_fields = ("scenario__title", "user__username", "notes")
    date_hierarchy = "played_date"
    readonly_fields = ("created_at",)


@admin.register(ScenarioImage)
class ScenarioImageAdmin(admin.ModelAdmin):
    list_display = ("scenario", "title", "order", "uploaded_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("scenario__title", "title")
    ordering = ("scenario", "order", "created_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ScenarioRecommendedSkill)
class ScenarioRecommendedSkillAdmin(admin.ModelAdmin):
    list_display = ("scenario", "name", "level", "order")
    list_filter = ("level",)
    search_fields = ("scenario__title", "name", "description")


@admin.register(ScenarioHandout)
class ScenarioHandoutAdmin(admin.ModelAdmin):
    list_display = ("scenario", "code", "name", "handout_number", "assigned_player_slot", "order")
    list_filter = ("is_secret",)
    search_fields = ("scenario__title", "code", "name", "title", "content")


@admin.register(ScenarioHandoutRecommendedSkill)
class ScenarioHandoutRecommendedSkillAdmin(admin.ModelAdmin):
    list_display = ("handout", "name", "level", "order")
    list_filter = ("level",)
    search_fields = ("handout__scenario__title", "handout__name", "name", "description")
