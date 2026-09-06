"""Keep the selected Google credential and its scopes atomic on PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

from allauth.socialaccount.models import SocialAccount, SocialLogin, SocialToken
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from accounts.google_oauth import store_google_integration_grant
from schedules.models import GoogleIntegration


@skipUnlessDBFeature("has_select_for_update")
class GoogleGrantConcurrencyTests(TransactionTestCase):
    def test_competing_accounts_leave_one_credential_with_matching_scopes(self):
        user = get_user_model().objects.create_user(username="competing-google-owner")
        accounts = [SocialAccount.objects.create(user=user, provider="google", uid=f"grant-{i}") for i in range(2)]
        scope_options = [GoogleIntegration.REQUIRED_CALENDAR_SCOPE, GoogleIntegration.REQUIRED_SHEETS_SCOPE]
        barrier = Barrier(2)

        def connect(index):
            close_old_connections()
            try:
                account = SocialAccount.objects.get(pk=accounts[index].pk)
                login = SocialLogin(
                    account=account, user=account.user, token=SocialToken(account=account, token=f"credential-{index}")
                )
                login.state = {"process": "connect"}
                login.google_integration_scopes = [scope_options[index]]
                barrier.wait(timeout=10)
                store_google_integration_grant(
                    sender=SocialLogin, request=SimpleNamespace(user=account.user), sociallogin=login
                )
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(connect, index) for index in range(2)]
            for future in futures:
                future.result(timeout=30)
        token = SocialToken.objects.get(account__user=user)
        selected = int(token.token.rsplit("-", 1)[1])
        integration = GoogleIntegration.objects.get(user=user)
        self.assertEqual(integration.scopes, [scope_options[selected]])
        self.assertEqual(token.account_id, accounts[selected].pk)
