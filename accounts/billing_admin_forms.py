import hashlib
import json

from django import forms
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.functional import cached_property

from accounts.models import PremiumSubscription

REVISION_SALT = "accounts.premium-subscription-admin"
CHANGED_MESSAGE = "課金情報が変更されています。ページを再読み込みして、内容を確認してから保存してください。"
INVALID_MESSAGE = "更新確認情報が無効です。ページを再読み込みしてください。"


def subscription_revision(record):
    # Include readonly columns and full datetime precision, even for writers
    # that do not update updated_at. Only a digest is sent to the browser.
    values = {field.attname: field.value_from_object(record) for field in record._meta.concrete_fields}
    digest = hashlib.sha256(json.dumps(values, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return {"record": record.pk, "digest": digest}


def validate_subscription_revision(record, token):
    try:
        revision = signing.loads(token or "", salt=REVISION_SALT)
    except signing.BadSignature as exc:
        raise ValidationError(INVALID_MESSAGE) from exc
    if revision != subscription_revision(record):
        raise ValidationError(CHANGED_MESSAGE)


class PremiumSubscriptionAdminForm(forms.ModelForm):
    billing_revision = forms.CharField(label="課金情報の更新確認", widget=forms.HiddenInput, required=False)

    class Meta:
        model = PremiumSubscription
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["billing_revision"] = signing.dumps(subscription_revision(self.instance), salt=REVISION_SALT)

    @cached_property
    def changed_data(self):
        return [name for name in super().changed_data if name != "billing_revision"]

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk:
            # The normal admin POST keeps its outer transaction open through
            # validation, save, related data and the Django admin log.
            with transaction.atomic():
                try:
                    current = PremiumSubscription.objects.select_for_update().get(pk=self.instance.pk)
                except PremiumSubscription.DoesNotExist as exc:
                    raise ValidationError(CHANGED_MESSAGE) from exc
                validate_subscription_revision(current, cleaned.get("billing_revision"))
        return cleaned
