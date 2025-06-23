from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, Friend, Group, GroupMembership, GroupInvitation
)
from .character_models import (
    CharacterSheet, CharacterSheet6th, 
    CharacterSkill, CharacterEquipment
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'nickname', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'nickname')
    ordering = ('username',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('追加情報', {'fields': ('nickname', 'trpg_history', 'profile_image')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('追加情報', {'fields': ('nickname', 'trpg_history', 'profile_image')}),
    )


@admin.register(Friend)
class FriendAdmin(admin.ModelAdmin):
    list_display = ('user', 'friend', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'friend__username', 'user__nickname', 'friend__nickname')
    

class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 1


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    inlines = [GroupMembershipInline]
    

@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('user__username', 'group__name')


@admin.register(GroupInvitation)
class GroupInvitationAdmin(admin.ModelAdmin):
    list_display = ('inviter', 'invitee', 'group', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('inviter__username', 'invitee__username', 'group__name')


class CharacterSkillInline(admin.TabularInline):
    model = CharacterSkill
    extra = 0
    fields = ('skill_name', 'base_value', 'occupation_points', 'interest_points', 'current_value')
    readonly_fields = ('current_value',)


class CharacterEquipmentInline(admin.TabularInline):
    model = CharacterEquipment
    extra = 0
    fields = ('item_type', 'name', 'quantity', 'description')


class CharacterSheet6thInline(admin.StackedInline):
    model = CharacterSheet6th
    fields = (
        'mental_disorder',
        ('idea_roll', 'luck_roll', 'know_roll'),
        'damage_bonus'
    )
    readonly_fields = ('idea_roll', 'luck_roll', 'know_roll', 'damage_bonus')




@admin.register(CharacterSheet)
class CharacterSheetAdmin(admin.ModelAdmin):
    list_display = ('name', 'edition', 'user', 'version', 'is_active', 'updated_at')
    list_filter = ('edition', 'is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'user__username', 'user__nickname', 'occupation')
    readonly_fields = ('created_at', 'updated_at', 'hit_points_max', 'magic_points_max', 
                      'sanity_starting', 'sanity_max')
    
    fieldsets = (
        ('基本情報', {
            'fields': (
                ('user', 'edition', 'version'),
                ('name', 'player_name'),
                ('age', 'gender'),
                ('occupation', 'birthplace', 'residence')
            )
        }),
        ('能力値', {
            'fields': (
                ('str_value', 'con_value', 'pow_value', 'dex_value'),
                ('app_value', 'siz_value', 'int_value', 'edu_value')
            )
        }),
        ('副次ステータス', {
            'fields': (
                ('hit_points_max', 'hit_points_current'),
                ('magic_points_max', 'magic_points_current'),
                ('sanity_starting', 'sanity_max', 'sanity_current')
            )
        }),
        ('バージョン管理', {
            'fields': ('parent_sheet', 'is_active'),
            'classes': ('collapse',)
        }),
        ('その他', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [CharacterSkillInline, CharacterEquipmentInline]
    
    def get_inlines(self, request, obj):
        """版に応じてインラインを変更"""
        inlines = [CharacterSkillInline, CharacterEquipmentInline]
        
        if obj and obj.edition == '6th':
            inlines.append(CharacterSheet6thInline)
        
        return inlines


@admin.register(CharacterSkill)
class CharacterSkillAdmin(admin.ModelAdmin):
    list_display = ('character_sheet', 'skill_name', 'current_value', 'base_value', 
                   'occupation_points', 'interest_points')
    list_filter = ('character_sheet__edition', 'skill_name')
    search_fields = ('character_sheet__name', 'skill_name', 'character_sheet__user__username')
    readonly_fields = ('current_value',)


@admin.register(CharacterEquipment)
class CharacterEquipmentAdmin(admin.ModelAdmin):
    list_display = ('character_sheet', 'name', 'item_type', 'quantity')
    list_filter = ('item_type', 'character_sheet__edition')
    search_fields = ('character_sheet__name', 'name', 'character_sheet__user__username')
