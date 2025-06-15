from django.contrib import admin
from .models import TRPGSession, SessionParticipant, HandoutInfo


class SessionParticipantInline(admin.TabularInline):
    model = SessionParticipant
    extra = 1


class HandoutInfoInline(admin.TabularInline):
    model = HandoutInfo
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(TRPGSession)
class TRPGSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'gm', 'group', 'status', 'visibility')
    list_filter = ('status', 'visibility', 'date', 'created_at')
    search_fields = ('title', 'description', 'gm__username', 'group__name')
    date_hierarchy = 'date'
    ordering = ('-date',)
    
    inlines = [SessionParticipantInline, HandoutInfoInline]
    
    fieldsets = (
        ('基本情報', {
            'fields': ('title', 'description', 'date', 'location')
        }),
        ('参加者情報', {
            'fields': ('gm', 'group')
        }),
        ('設定', {
            'fields': ('status', 'visibility', 'youtube_url', 'duration_minutes')
        }),
    )


@admin.register(SessionParticipant)
class SessionParticipantAdmin(admin.ModelAdmin):
    list_display = ('session', 'user', 'role', 'character_name')
    list_filter = ('role',)
    search_fields = ('session__title', 'user__username', 'character_name')
    

@admin.register(HandoutInfo)
class HandoutInfoAdmin(admin.ModelAdmin):
    list_display = ('title', 'session', 'participant', 'is_secret', 'created_at')
    list_filter = ('is_secret', 'created_at')
    search_fields = ('title', 'content', 'session__title', 'participant__user__username')
    readonly_fields = ('created_at', 'updated_at')
