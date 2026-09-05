from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from rest_framework.authtoken.models import Token

from accounts.google_identity import complete_google_login


@skipUnlessDBFeature("has_select_for_update")
class GoogleIdentityConcurrencyTests(TransactionTestCase):
    def test_simultaneous_first_login_creates_one_account_and_token(self):
        barrier = Barrier(2)
        guard = Lock()
        entered = 0
        original = SocialAccount.objects.create

        def synchronized_create(**kwargs):
            nonlocal entered
            with guard:
                entered += 1
                wait = entered <= 2
            if wait:
                barrier.wait(timeout=15)
            return original(**kwargs)

        def login():
            close_old_connections()
            try:
                user, created, token = complete_google_login(
                    {"sub": "concurrent-id", "email": "concurrent@gmail.com", "email_verified": True},
                    AnonymousUser(),
                )
                return user.pk, created, token.key
            finally:
                close_old_connections()

        with patch("accounts.google_identity.SocialAccount.objects.create", side_effect=synchronized_create):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: login(), range(2)))
        self.assertEqual(len({result[0] for result in results}), 1)
        self.assertEqual(len({result[2] for result in results}), 1)
        self.assertEqual(sorted(result[1] for result in results), [False, True])
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(SocialAccount.objects.count(), 1)
        self.assertEqual(EmailAddress.objects.filter(verified=True).count(), 1)
        self.assertEqual(Token.objects.count(), 1)
