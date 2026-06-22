import csv

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import models
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from accounts.billing import create_premium_audit_log, premium_access_code_metadata
from .models import (
    CustomUser, Friend, Group, GroupMembership, GroupInvitation, GroupInviteLink,
    PremiumAccessCode, PremiumAccessCodeRedemption,
    PremiumAuditLog, PremiumSubscription, StripeWebhookEvent
)
from .character_models import (
    CharacterSheet, CharacterSheet6th, 
    CharacterSkill, CharacterEquipment
)


class PremiumSubscriptionInline(admin.StackedInline):
    model = PremiumSubscription
    extra = 0
    can_delete = False
    fields = (
        ('access_source', 'subscription_status'),
        ('access_state', 'access_reason'),
        ('stripe_customer_id', 'stripe_customer_link'),
        ('stripe_subscription_id', 'stripe_subscription_link'),
        ('stripe_price_id', 'billing_interval'),
        ('current_period_end', 'premium_expires_at'),
        ('cancel_at_period_end', 'revoked_at'),
        'revoked_reason',
        ('last_payment_failed_at', 'last_refund_or_dispute_at'),
        'last_webhook_event_id',
        ('created_at', 'updated_at'),
    )
    readonly_fields = (
        'access_source',
        'subscription_status',
        'access_state',
        'access_reason',
        'stripe_customer_id',
        'stripe_customer_link',
        'stripe_subscription_id',
        'stripe_subscription_link',
        'stripe_price_id',
        'billing_interval',
        'current_period_end',
        'premium_expires_at',
        'cancel_at_period_end',
        'revoked_at',
        'revoked_reason',
        'last_payment_failed_at',
        'last_refund_or_dispute_at',
        'last_webhook_event_id',
        'created_at',
        'updated_at',
    )

    def has_add_permission(self, request, obj):
        return False

    @admin.display(description='Stripe customer')
    def stripe_customer_link(self, obj):
        return stripe_dashboard_link('customers', obj.stripe_customer_id)

    @admin.display(description='Stripe subscription')
    def stripe_subscription_link(self, obj):
        return stripe_dashboard_link('subscriptions', obj.stripe_subscription_id)

    @admin.display(description='Access state')
    def access_state(self, obj):
        return subscription_access_state(obj)

    @admin.display(description='Access reason')
    def access_reason(self, obj):
        return subscription_access_reason(obj)


class PremiumAccessCodeRedemptionInline(admin.TabularInline):
    model = PremiumAccessCodeRedemption
    extra = 0
    fields = (
        'access_code_link',
        'code_label',
        'code_campaign_name',
        'code_status',
        'code_expires_at',
        'user_link',
        'redeemed_at',
    )
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('access_code', 'user')

    @admin.display(description='Access code')
    def access_code_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:accounts_premiumaccesscode_change', args=[obj.access_code.pk]),
            obj.access_code,
        )

    @admin.display(description='Code label')
    def code_label(self, obj):
        return obj.access_code.label or '-'

    @admin.display(description='Code campaign')
    def code_campaign_name(self, obj):
        return obj.access_code.campaign_name or '-'

    @admin.display(description='Code status')
    def code_status(self, obj):
        return obj.access_code.status_label

    @admin.display(description='Code expires')
    def code_expires_at(self, obj):
        return obj.access_code.expires_at

    @admin.display(description='User')
    def user_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:accounts_customuser_change', args=[obj.user.pk]),
            obj.user,
        )


class PremiumAuditLogInline(admin.TabularInline):
    model = PremiumAuditLog
    fk_name = 'user'
    extra = 0
    fields = ('action', 'source', 'actor', 'reason', 'stripe_event_id', 'created_at')
    readonly_fields = ('action', 'source', 'actor', 'reason', 'stripe_event_id', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj):
        return False


def stripe_dashboard_link(resource, object_id):
    if not object_id:
        return '-'
    return format_html(
        '<a href="https://dashboard.stripe.com/{}/{}" target="_blank" rel="noopener">{}</a>',
        resource,
        object_id,
        object_id,
    )


def subscription_access_state(subscription):
    return 'active' if subscription.expected_user_premium_access else 'inactive'


def subscription_access_reason(subscription):
    if subscription.has_manual_premium_override and not subscription.is_access_active:
        return 'manual: active override'
    if subscription.revoked_at:
        return f'revoked: {subscription.revoked_reason or "no reason"}'
    if subscription.last_refund_or_dispute_at and not getattr(
        settings,
        'STRIPE_REVOKE_ON_REFUND_OR_DISPUTE',
        True,
    ):
        return 'refund/dispute detected: manual review'
    if subscription.access_source == 'stripe':
        if subscription.subscription_status in PremiumSubscription.ACTIVE_STATUSES:
            if subscription.cancel_at_period_end:
                return 'stripe: active until period end'
            return f'stripe: {subscription.subscription_status}'
        return f'stripe: {subscription.subscription_status or "not subscribed"}'
    if subscription.access_source == 'promo_code':
        if subscription.premium_expires_at:
            if subscription.is_promo_active:
                return 'promo code: active until expiration'
            return 'promo code: expired'
        if subscription.is_promo_active:
            return 'promo code: indefinite'
        return f'promo code: {subscription.subscription_status or "inactive"}'
    if subscription.is_access_active:
        return f'{subscription.access_source or "manual"}: active'
    return subscription.subscription_status or subscription.access_source or 'inactive'


class PaymentIssueListFilter(admin.SimpleListFilter):
    title = 'Payment issue'
    parameter_name = 'payment_issue'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Has failed payment'),
            ('no', 'No failed payment'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(last_payment_failed_at__isnull=False)
        if self.value() == 'no':
            return queryset.filter(last_payment_failed_at__isnull=True)
        return queryset


class RefundOrDisputeListFilter(admin.SimpleListFilter):
    title = 'Refund/dispute'
    parameter_name = 'refund_or_dispute'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Detected'),
            ('active', 'Detected and access active'),
            ('no', 'Not detected'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(last_refund_or_dispute_at__isnull=False)
        if self.value() == 'active':
            return queryset.filter(
                last_refund_or_dispute_at__isnull=False,
                revoked_at__isnull=True,
                user__is_premium=True,
            )
        if self.value() == 'no':
            return queryset.filter(last_refund_or_dispute_at__isnull=True)
        return queryset


def active_subscription_query(now=None):
    now = now or timezone.now()
    return models.Q(
        revoked_at__isnull=True,
        subscription_status__in=PremiumSubscription.ACTIVE_STATUSES,
    ) | models.Q(
        revoked_at__isnull=True,
        subscription_status=PremiumSubscription.PROMO_STATUS,
        access_source='promo_code',
    ) & (
        models.Q(premium_expires_at__isnull=True)
        | models.Q(premium_expires_at__gt=now)
    )


class SubscriptionOperationalIssueFilter(admin.SimpleListFilter):
    title = 'Operational issue'
    parameter_name = 'operational_issue'

    def lookups(self, request, model_admin):
        return (
            ('stale_user_flag', 'User premium flag mismatch'),
            ('expired_promo', 'Expired promo access'),
            ('promo_expiring_soon', 'Promo access expiring within 7 days'),
            ('canceling', 'Stripe canceling at period end'),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        active_q = active_subscription_query(now)
        if self.value() == 'stale_user_flag':
            stale_ids = [
                record.pk
                for record in queryset.select_related('user')
                if record.user.is_premium != record.expected_user_premium_access
            ]
            return queryset.filter(pk__in=stale_ids)
        if self.value() == 'expired_promo':
            return queryset.filter(
                subscription_status=PremiumSubscription.PROMO_STATUS,
                access_source='promo_code',
                premium_expires_at__isnull=False,
                premium_expires_at__lte=now,
                revoked_at__isnull=True,
            )
        if self.value() == 'promo_expiring_soon':
            return queryset.filter(
                subscription_status=PremiumSubscription.PROMO_STATUS,
                access_source='promo_code',
                premium_expires_at__isnull=False,
                premium_expires_at__gt=now,
                premium_expires_at__lte=now + timezone.timedelta(days=7),
                revoked_at__isnull=True,
            )
        if self.value() == 'canceling':
            return queryset.filter(
                subscription_status__in=PremiumSubscription.ACTIVE_STATUSES,
                access_source='stripe',
                cancel_at_period_end=True,
                revoked_at__isnull=True,
            )
        return queryset


class WebhookOperationalIssueFilter(admin.SimpleListFilter):
    title = 'Operational issue'
    parameter_name = 'webhook_issue'

    def lookups(self, request, model_admin):
        return (
            ('failed', 'Failed'),
            ('processing', 'Processing'),
            ('stale_processing', 'Processing for over 15 minutes'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'failed':
            return queryset.filter(processing_status=StripeWebhookEvent.STATUS_FAILED)
        if self.value() == 'processing':
            return queryset.filter(processing_status=StripeWebhookEvent.STATUS_PROCESSING)
        if self.value() == 'stale_processing':
            return queryset.filter(
                processing_status=StripeWebhookEvent.STATUS_PROCESSING,
                processed_at__lte=timezone.now() - timezone.timedelta(minutes=15),
            )
        return queryset


class PremiumAccessCodeStatusFilter(admin.SimpleListFilter):
    title = 'Code status'
    parameter_name = 'code_status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('exhausted', 'Exhausted'),
            ('revoked', 'Revoked'),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'active':
            return queryset.filter(
                revoked_at__isnull=True,
                use_count__lt=models.F('max_uses'),
            ).filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
        if self.value() == 'expired':
            return queryset.filter(
                revoked_at__isnull=True,
                expires_at__isnull=False,
                expires_at__lte=now,
            )
        if self.value() == 'exhausted':
            return queryset.filter(
                revoked_at__isnull=True,
                use_count__gte=models.F('max_uses'),
            )
        if self.value() == 'revoked':
            return queryset.filter(revoked_at__isnull=False)
        return queryset


def manual_override_user_ids():
    latest_manual_logs = {}
    logs = (
        PremiumAuditLog.objects
        .filter(source='manual', action__in=('granted', 'revoked'))
        .order_by('user_id', '-created_at', '-pk')
        .values_list('user_id', 'action')
    )
    for user_id, action in logs:
        latest_manual_logs.setdefault(user_id, action)
    return [
        user_id
        for user_id, action in latest_manual_logs.items()
        if action == 'granted'
    ]


class UserPremiumSourceFilter(admin.SimpleListFilter):
    title = 'Premium source'
    parameter_name = 'premium_source'

    def lookups(self, request, model_admin):
        return (
            ('stripe', 'Stripe subscription'),
            ('promo_code', 'Premium access code'),
            ('manual_override', 'Manual override'),
            ('manual_without_subscription', 'Manual without billing record'),
            ('none', 'No premium access'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'stripe':
            return queryset.filter(premium_subscription__access_source='stripe')
        if self.value() == 'promo_code':
            return queryset.filter(premium_subscription__access_source='promo_code')
        if self.value() == 'manual_override':
            return queryset.filter(pk__in=manual_override_user_ids())
        if self.value() == 'manual_without_subscription':
            return queryset.filter(
                pk__in=manual_override_user_ids(),
                premium_subscription__isnull=True,
            )
        if self.value() == 'none':
            return queryset.filter(is_premium=False, premium_subscription__isnull=True)
        return queryset


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username',
        'email',
        'nickname',
        'first_name',
        'last_name',
        'is_premium',
        'premium_access_source',
        'premium_expires_at',
        'premium_status',
        'is_staff',
    )
    list_filter = (
        'is_premium',
        UserPremiumSourceFilter,
        'is_staff',
        'is_superuser',
        'is_active',
        'date_joined',
    )
    search_fields = ('username', 'first_name', 'last_name', 'email', 'nickname')
    ordering = ('username',)
    inlines = (
        PremiumSubscriptionInline,
        PremiumAccessCodeRedemptionInline,
        PremiumAuditLogInline,
    )
    
    fieldsets = UserAdmin.fieldsets + (
        ('追加情報', {'fields': ('nickname', 'trpg_history', 'profile_image', 'is_premium')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('追加情報', {'fields': ('nickname', 'trpg_history', 'profile_image', 'is_premium')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('premium_subscription')

    def save_model(self, request, obj, form, change):
        previous_is_premium = None
        if change and obj.pk:
            previous_is_premium = (
                type(obj).objects
                .filter(pk=obj.pk)
                .values_list('is_premium', flat=True)
                .first()
            )

        super().save_model(request, obj, form, change)

        if previous_is_premium is None:
            should_log = obj.is_premium
        else:
            should_log = previous_is_premium != obj.is_premium
        if not should_log:
            return

        create_premium_audit_log(
            obj,
            action='granted' if obj.is_premium else 'revoked',
            source='manual',
            reason='Manual premium access updated in Django admin',
            metadata={'admin_model': 'CustomUser', 'field': 'is_premium'},
            actor=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
        )

    @admin.display(description='Premium source')
    def premium_access_source(self, obj):
        subscription = getattr(obj, 'premium_subscription', None)
        if subscription:
            return subscription.access_source
        return 'manual' if obj.is_premium else ''

    @admin.display(description='Premium expires')
    def premium_expires_at(self, obj):
        subscription = getattr(obj, 'premium_subscription', None)
        return subscription.premium_expires_at if subscription else None

    @admin.display(description='Premium status')
    def premium_status(self, obj):
        subscription = getattr(obj, 'premium_subscription', None)
        if subscription:
            return subscription_access_reason(subscription)
        return 'manual' if obj.is_premium else ''


@admin.register(Friend)
class FriendAdmin(admin.ModelAdmin):
    list_display = ('user', 'friend', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'friend__username', 'user__nickname', 'friend__nickname')


@admin.register(PremiumSubscription)
class PremiumSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user_link',
        'access_state',
        'access_reason',
        'subscription_status',
        'access_source',
        'stripe_customer_link',
        'stripe_subscription_link',
        'stripe_price_id',
        'billing_interval',
        'current_period_end',
        'premium_expires_at',
        'cancel_at_period_end',
        'revoked_at',
        'last_payment_failed_at',
        'last_refund_or_dispute_at',
        'updated_at',
    )
    list_filter = (
        SubscriptionOperationalIssueFilter,
        PaymentIssueListFilter,
        RefundOrDisputeListFilter,
        'subscription_status',
        'access_source',
        'billing_interval',
        'cancel_at_period_end',
        'revoked_at',
        'last_refund_or_dispute_at',
        'last_payment_failed_at',
        'created_at',
        'updated_at',
    )
    search_fields = (
        'user__username',
        'user__email',
        'user__nickname',
        'stripe_customer_id',
        'stripe_subscription_id',
        'stripe_price_id',
        'last_webhook_event_id',
    )
    readonly_fields = (
        'created_at',
        'updated_at',
        'last_payment_failed_at',
        'last_refund_or_dispute_at',
        'last_webhook_event_id',
        'stripe_customer_link',
        'stripe_subscription_link',
    )
    actions = (
        'restore_selected_access',
        'revoke_selected_access',
        'sync_selected_user_access',
        'mark_refund_or_dispute_reviewed',
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    @admin.display(description='User')
    def user_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:accounts_customuser_change', args=[obj.user.pk]),
            obj.user,
        )

    @admin.display(description='Access state')
    def access_state(self, obj):
        return subscription_access_state(obj)

    @admin.display(description='Access reason')
    def access_reason(self, obj):
        return subscription_access_reason(obj)

    @admin.display(description='Stripe customer')
    def stripe_customer_link(self, obj):
        return stripe_dashboard_link('customers', obj.stripe_customer_id)

    @admin.display(description='Stripe subscription')
    def stripe_subscription_link(self, obj):
        return stripe_dashboard_link('subscriptions', obj.stripe_subscription_id)

    @admin.action(description='選択した課金レコードのプレミアム権限を停止する')
    def revoke_selected_access(self, request, queryset):
        count = 0
        for record in queryset.select_related('user'):
            record.revoke_access('Revoked manually by admin action', save=True)
            create_premium_audit_log(
                record.user,
                action='revoked',
                source=record.access_source,
                reason='Revoked manually by admin action',
                metadata={'subscription_id': record.pk},
                actor=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            )
            count += 1
        self.message_user(request, f'{count}件のプレミアム権限を停止しました。')

    @admin.action(description='選択した課金レコードの失効状態を解除して権限を再同期する')
    def restore_selected_access(self, request, queryset):
        changed = 0
        for record in queryset.select_related('user'):
            before = record.user.is_premium
            record.revoked_at = None
            record.revoked_reason = ''
            record.save(update_fields=['revoked_at', 'revoked_reason', 'updated_at'])
            record.sync_user_premium_access()
            record.user.refresh_from_db()
            if before != record.user.is_premium:
                changed += 1
            create_premium_audit_log(
                record.user,
                action='restored',
                source=record.access_source,
                reason='Premium access restored manually by admin action',
                metadata={'subscription_id': record.pk},
                actor=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            )
        self.message_user(request, f'{changed}件のユーザー権限を復旧しました。')

    @admin.action(description='選択した課金レコードからユーザー権限を再同期する')
    def sync_selected_user_access(self, request, queryset):
        changed = 0
        for record in queryset.select_related('user'):
            before = record.user.is_premium
            record.sync_user_premium_access()
            record.user.refresh_from_db()
            if before != record.user.is_premium:
                changed += 1
                create_premium_audit_log(
                    record.user,
                    action='granted' if record.user.is_premium else 'revoked',
                    source=record.access_source,
                    reason='Premium access synced manually by admin action',
                    metadata={'subscription_id': record.pk},
                    actor=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
                )
        self.message_user(request, f'{changed}件のユーザー権限を再同期しました。')

    @admin.action(description='選択した返金/チャージバック検知を確認済みにする')
    def mark_refund_or_dispute_reviewed(self, request, queryset):
        count = 0
        for record in queryset.select_related('user').filter(last_refund_or_dispute_at__isnull=False):
            detected_at = record.last_refund_or_dispute_at
            record.last_refund_or_dispute_at = None
            record.save(update_fields=['last_refund_or_dispute_at', 'updated_at'])
            create_premium_audit_log(
                record.user,
                action='reviewed',
                source=record.access_source,
                reason='Refund/dispute manually reviewed by admin action',
                metadata={
                    'subscription_id': record.pk,
                    'last_refund_or_dispute_at': detected_at.isoformat() if detected_at else '',
                },
                actor=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            )
            count += 1
        self.message_user(request, f'{count}件の返金/チャージバック検知を確認済みにしました。')


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'event_type', 'processing_status', 'processed_at')
    list_filter = (WebhookOperationalIssueFilter, 'processing_status', 'event_type', 'processed_at')
    search_fields = ('event_id', 'event_type', 'error_message')
    readonly_fields = ('event_id', 'event_type', 'processing_status', 'error_message', 'processed_at')


@admin.register(PremiumAccessCode)
class PremiumAccessCodeAdmin(admin.ModelAdmin):
    list_display = (
        'label',
        'campaign_name',
        'code_status',
        'max_uses',
        'use_count',
        'remaining_uses',
        'redemption_list',
        'expires_at',
        'revoked_at',
        'created_by',
        'created_at',
    )
    list_filter = (PremiumAccessCodeStatusFilter, 'campaign_name', 'expires_at', 'revoked_at', 'created_at')
    search_fields = (
        'label',
        'campaign_name',
        'note',
        'created_by__username',
        'created_by__email',
        'redemptions__user__username',
        'redemptions__user__email',
        'redemptions__user__nickname',
    )
    readonly_fields = ('code_digest', 'use_count', 'created_at')
    inlines = (PremiumAccessCodeRedemptionInline,)
    actions = ('revoke_codes', 'revoke_code_granted_access', 'export_codes_csv')

    @admin.display(description='Remaining')
    def remaining_uses(self, obj):
        return max(obj.max_uses - obj.use_count, 0)

    @admin.display(description='Status')
    def code_status(self, obj):
        return obj.status_label

    @admin.display(description='Redemptions')
    def redemption_list(self, obj):
        redemptions = obj.redemptions.select_related('user').order_by('-redeemed_at')[:5]
        if not redemptions:
            return '-'
        return format_html_join(
            ', ',
            '<a href="{}">{}</a>',
            (
                (
                    reverse('admin:accounts_customuser_change', args=[redemption.user.pk]),
                    redemption.user.username,
                )
                for redemption in redemptions
            ),
        )

    @admin.action(description='選択したプレミアムコードを停止する')
    def revoke_codes(self, request, queryset):
        updated = queryset.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
        self.message_user(request, f'{updated}件のプレミアムコードを停止しました。')

    @admin.action(description='選択したコードで付与済みのプレミアム権限を失効する')
    def revoke_code_granted_access(self, request, queryset):
        count = 0
        redemptions = (
            PremiumAccessCodeRedemption.objects
            .select_related('access_code', 'user')
            .filter(access_code__in=queryset)
        )
        for redemption in redemptions:
            record = (
                PremiumSubscription.objects
                .select_related('user')
                .filter(
                    user=redemption.user,
                    access_source='promo_code',
                    subscription_status=PremiumSubscription.PROMO_STATUS,
                    revoked_at__isnull=True,
                )
                .first()
            )
            if record is None or not record.user.is_premium:
                continue
            record.revoke_access(
                'Premium access code revoked by admin action',
                save=True,
                preserve_manual_override=True,
            )
            create_premium_audit_log(
                record.user,
                action='revoked',
                source='promo_code',
                reason='Premium access code revoked by admin action',
                metadata={
                    **premium_access_code_metadata(redemption.access_code),
                    'subscription_id': record.pk,
                },
                actor=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            )
            count += 1
        self.message_user(request, f'{count}件のコード由来プレミアム権限を失効しました。')

    @admin.action(description='選択したプレミアムコードをCSV出力する')
    def export_codes_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="premium-access-codes.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow([
            'id',
            'label',
            'campaign_name',
            'status',
            'max_uses',
            'use_count',
            'remaining_uses',
            'expires_at',
            'revoked_at',
            'created_by',
            'created_at',
            'redemptions',
            'redemption_user_emails',
            'redemption_details',
        ])
        for access_code in queryset.select_related('created_by').prefetch_related('redemptions__user'):
            redemptions = list(access_code.redemptions.all())
            redemption_usernames = [
                redemption.user.username
                for redemption in redemptions
            ]
            redemption_emails = [
                redemption.user.email
                for redemption in redemptions
                if redemption.user.email
            ]
            redemption_details = [
                f'{redemption.user.username} <{redemption.user.email}> at {redemption.redeemed_at.isoformat()}'
                for redemption in redemptions
            ]
            writer.writerow([
                access_code.pk,
                access_code.label,
                access_code.campaign_name,
                access_code.status_label,
                access_code.max_uses,
                access_code.use_count,
                max(access_code.max_uses - access_code.use_count, 0),
                access_code.expires_at.isoformat() if access_code.expires_at else '',
                access_code.revoked_at.isoformat() if access_code.revoked_at else '',
                access_code.created_by.username if access_code.created_by else '',
                access_code.created_at.isoformat() if access_code.created_at else '',
                ','.join(redemption_usernames),
                ','.join(redemption_emails),
                ' | '.join(redemption_details),
            ])
        return response


@admin.register(PremiumAccessCodeRedemption)
class PremiumAccessCodeRedemptionAdmin(admin.ModelAdmin):
    list_display = ('access_code', 'user', 'user_email', 'redeemed_at')
    list_filter = ('redeemed_at',)
    search_fields = (
        'access_code__label',
        'user__username',
        'user__email',
        'user__nickname',
    )
    readonly_fields = ('access_code', 'user', 'redeemed_at')

    @admin.display(description='User email')
    def user_email(self, obj):
        return obj.user.email


class PremiumAuditActorFilter(admin.SimpleListFilter):
    title = 'Audit actor'
    parameter_name = 'audit_actor'

    def lookups(self, request, model_admin):
        return (
            ('system', 'System or webhook'),
            ('admin', 'Admin/user action'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'system':
            return queryset.filter(actor__isnull=True)
        if self.value() == 'admin':
            return queryset.filter(actor__isnull=False)
        return queryset


@admin.register(PremiumAuditLog)
class PremiumAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'user_link',
        'actor_link',
        'action',
        'source',
        'reason',
        'stripe_event_id',
        'metadata_summary',
        'created_at',
    )
    list_filter = (PremiumAuditActorFilter, 'action', 'source', 'created_at')
    search_fields = (
        'user__username',
        'user__email',
        'user__nickname',
        'actor__username',
        'actor__email',
        'actor__nickname',
        'reason',
        'stripe_event_id',
    )
    readonly_fields = (
        'user',
        'actor',
        'action',
        'source',
        'reason',
        'stripe_event_id',
        'metadata',
        'created_at',
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'actor')

    @admin.display(description='User')
    def user_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:accounts_customuser_change', args=[obj.user.pk]),
            obj.user,
        )

    @admin.display(description='Actor')
    def actor_link(self, obj):
        if not obj.actor:
            return 'system'
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:accounts_customuser_change', args=[obj.actor.pk]),
            obj.actor,
        )

    @admin.display(description='Metadata')
    def metadata_summary(self, obj):
        if not obj.metadata:
            return '-'
        parts = [
            f'{key}={value}'
            for key, value in sorted(obj.metadata.items())
        ]
        summary = ', '.join(parts)
        return summary[:120] + ('...' if len(summary) > 120 else '')
    

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


@admin.register(GroupInviteLink)
class GroupInviteLinkAdmin(admin.ModelAdmin):
    list_display = ('group', 'created_by', 'use_count', 'max_uses', 'expires_at', 'revoked_at', 'created_at')
    list_filter = ('expires_at', 'revoked_at', 'created_at')
    search_fields = ('group__name', 'created_by__username', 'created_by__nickname')
    readonly_fields = ('token_digest', 'use_count', 'created_at')


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
