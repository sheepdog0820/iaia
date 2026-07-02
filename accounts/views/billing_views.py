import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.billing import (
    PremiumCodeRedeemError,
    create_checkout_session,
    create_portal_session,
    get_configured_checkout_plans,
    get_stripe,
    handle_checkout_completed,
    mark_invoice_payment_failed,
    mark_invoice_payment_succeeded,
    mark_refund_or_dispute,
    redeem_premium_access_code,
    sync_subscription_object,
)
from accounts.models import PremiumSubscription, StripeWebhookEvent

logger = logging.getLogger("tableno.billing")


def is_checkout_enabled():
    return bool(getattr(settings, "STRIPE_CHECKOUT_ENABLED", False))


class BillingPageView(TemplateView):
    template_name = "account/billing.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subscription = PremiumSubscription.objects.filter(user=self.request.user).first()
        context["subscription"] = subscription
        checkout_enabled = is_checkout_enabled()
        configured_plans = get_configured_checkout_plans()
        context["checkout_enabled"] = checkout_enabled
        context["stripe_configured"] = bool(checkout_enabled and settings.STRIPE_SECRET_KEY and configured_plans)
        context["checkout_price_options"] = configured_plans if checkout_enabled else []
        context["refund_or_dispute_auto_revoke"] = getattr(
            settings,
            "STRIPE_REVOKE_ON_REFUND_OR_DISPUTE",
            True,
        )
        return context


class BillingSuccessView(BillingPageView):
    template_name = "account/billing_success.html"


class BillingCancelView(BillingPageView):
    template_name = "account/billing_cancel.html"


class CheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not is_checkout_enabled():
            return Response(
                {"error": "Stripe Checkout is disabled until billing verification is complete"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            session = create_checkout_session(request, plan=request.data.get("plan", "monthly"))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ImproperlyConfigured as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception:
            logger.exception("Stripe checkout session creation failed")
            return Response(
                {"error": "Stripe service is temporarily unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"url": session.url})


class PortalSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            session = create_portal_session(request)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ImproperlyConfigured as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception:
            logger.exception("Stripe portal session creation failed")
            return Response(
                {"error": "Stripe service is temporarily unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"url": session.url})


class RedeemPremiumCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_code = request.data.get("code", "")
        try:
            access_code, redeemed = redeem_premium_access_code(request.user, raw_code)
        except PremiumCodeRedeemError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "redeemed": redeemed,
                "is_premium": request.user.has_premium_access,
                "label": access_code.label,
                "message": "プレミアム権限を付与しました。" if redeemed else "既にプレミアム権限があります。",
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not settings.STRIPE_WEBHOOK_SECRET:
            return Response(
                {"error": "STRIPE_WEBHOOK_SECRET is required"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        signature = request.META.get("HTTP_STRIPE_SIGNATURE")
        if not signature:
            return Response({"error": "Missing Stripe signature"}, status=status.HTTP_400_BAD_REQUEST)

        stripe = get_stripe()
        try:
            event = stripe.Webhook.construct_event(
                payload=request.body,
                sig_header=signature,
                secret=settings.STRIPE_WEBHOOK_SECRET,
            )
        except Exception:
            return Response({"error": "Invalid Stripe webhook"}, status=status.HTTP_400_BAD_REQUEST)

        event_id = event.get("id")
        event_type = event.get("type")
        if not event_id or not event_type:
            return Response(
                {"error": "Invalid Stripe webhook event"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            webhook_event, _ = StripeWebhookEvent.objects.get_or_create(
                event_id=event_id,
                defaults={
                    "event_type": event_type,
                    "processing_status": StripeWebhookEvent.STATUS_PROCESSING,
                },
            )
        except IntegrityError:
            webhook_event = StripeWebhookEvent.objects.get(event_id=event_id)

        if webhook_event.processing_status == StripeWebhookEvent.STATUS_SUCCEEDED:
            return Response({"received": True, "duplicate": True})

        try:
            with transaction.atomic():
                webhook_event = StripeWebhookEvent.objects.select_for_update().get(event_id=event_id)
                if webhook_event.processing_status == StripeWebhookEvent.STATUS_SUCCEEDED:
                    return Response({"received": True, "duplicate": True})
                webhook_event.event_type = event_type
                webhook_event.processing_status = StripeWebhookEvent.STATUS_PROCESSING
                webhook_event.error_message = ""
                webhook_event.processed_at = timezone.now()
                webhook_event.save(
                    update_fields=[
                        "event_type",
                        "processing_status",
                        "error_message",
                        "processed_at",
                    ]
                )
                data_object = event.get("data", {}).get("object", {})
                if event_type == "checkout.session.completed":
                    handle_checkout_completed(data_object, event_id=event_id)
                elif event_type in {
                    "customer.subscription.created",
                    "customer.subscription.updated",
                    "customer.subscription.deleted",
                }:
                    sync_subscription_object(data_object, event_id=event_id)
                elif event_type == "invoice.payment_failed":
                    mark_invoice_payment_failed(data_object, event_id=event_id)
                elif event_type == "invoice.payment_succeeded":
                    mark_invoice_payment_succeeded(data_object, event_id=event_id)
                elif event_type in {
                    "charge.refunded",
                    "charge.dispute.created",
                    "charge.dispute.closed",
                }:
                    mark_refund_or_dispute(data_object, event_type=event_type, event_id=event_id)
                webhook_event.processing_status = StripeWebhookEvent.STATUS_SUCCEEDED
                webhook_event.error_message = ""
                webhook_event.processed_at = timezone.now()
                webhook_event.save(
                    update_fields=[
                        "processing_status",
                        "error_message",
                        "processed_at",
                    ]
                )
        except IntegrityError:
            return Response({"received": True, "duplicate": True})
        except Exception as exc:
            StripeWebhookEvent.objects.filter(event_id=event_id).update(
                event_type=event_type,
                processing_status=StripeWebhookEvent.STATUS_FAILED,
                error_message=str(exc)[:2000],
                processed_at=timezone.now(),
            )
            return Response(
                {"received": False, "error": "Webhook processing failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"received": True})
