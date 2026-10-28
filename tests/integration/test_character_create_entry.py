"""The unversioned creation URL offers both supported editions, without writes."""

from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import CharacterSheet


class EntryLinks(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("id", "").startswith("create-entry-"):
            self.links[attrs["id"]] = attrs.get("href")


class CharacterCreateEntryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="creation-entry-fixture", email="creation-entry@example.test"
        )
        EmailAddress.objects.create(user=cls.user, email=cls.user.email, primary=True, verified=True)

    def test_anonymous_entry_requires_login_and_preserves_next(self):
        path = reverse("character_create")
        for method in ("get", "head", "post"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 302)
                location = urlsplit(response["Location"])
                self.assertEqual(location.path, reverse("account_login"))
                self.assertEqual(parse_qs(location.query), {"next": [path]})
        self.assertFalse(CharacterSheet.objects.exists())

    def test_authenticated_entry_renders_japanese_edition_choices(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("character_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/character_create_entry.html")
        self.assertContains(response, "キャラクターシート作成")
        self.assertContains(response, "クトゥルフ神話TRPGの版を選択してください。")
        self.assertContains(response, "6版キャラクター作成")
        self.assertContains(response, "7版キャラクター作成")
        self.assertContains(response, "キャラクター一覧に戻る")
        self.assertEqual(
            EntryLinks(response.content.decode()).links,
            {
                "create-entry-6th": reverse("character_create_6th"),
                "create-entry-7th": reverse("character_create_7th"),
                "create-entry-list": reverse("character_list"),
            },
        )
        self.assertFalse(CharacterSheet.objects.exists())

    def test_choice_links_render_existing_edition_forms(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("character_create"))
        links = EntryLinks(response.content.decode()).links
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                response = self.client.get(links[f"create-entry-{edition}"])
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, f"accounts/character_{edition}_create.html")
                self.assertEqual(response.context["edition"], edition)
                self.assertContains(response, 'name="name"')
        self.assertEqual(self.client.get(links["create-entry-list"]).status_code, 200)
        self.assertFalse(CharacterSheet.objects.exists())

    def test_authenticated_head_is_read_only(self):
        self.client.force_login(self.user)
        response = self.client.head(reverse("character_create"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        self.assertFalse(CharacterSheet.objects.exists())

    def test_authenticated_post_cannot_create_a_character(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("character_create"), {"name": "unexpected-write", "edition": "7th"})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(set(response["Allow"].split(", ")), {"GET", "HEAD", "OPTIONS"})
        self.assertFalse(CharacterSheet.objects.exists())

    def test_untrusted_query_does_not_select_edit_or_redirect(self):
        self.client.force_login(self.user)
        path = reverse("character_create")
        response = self.client.get(path, {"edition": "7th", "id": "999", "next": "https://invalid.example.test"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "invalid.example.test")
        self.assertEqual(
            EntryLinks(response.content.decode()).links["create-entry-7th"], reverse("character_create_7th")
        )
        self.assertFalse(CharacterSheet.objects.exists())
