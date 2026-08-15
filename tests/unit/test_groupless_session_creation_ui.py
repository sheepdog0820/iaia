import re
from pathlib import Path

from django.test import SimpleTestCase


class GrouplessSessionCreationUITests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = Path("templates/schedules/calendar.html").read_text(encoding="utf-8")

    def test_group_field_is_optional_and_explains_groupless_mode(self):
        self.assertIn('for="sessionGroup" class="form-label">グループ（任意）</label>', self.template)
        group_select = re.search(r'<select class="form-select" id="sessionGroup"([^>]*)>', self.template)
        self.assertIsNotNone(group_select)
        self.assertNotIn("required", group_select.group(1))
        self.assertIn('<option value="">グループなし（個別セッション）</option>', self.template)

    def test_groupless_default_is_private_and_group_scope_is_disabled(self):
        self.assertIn('<option value="group" id="sessionGroupVisibilityOption" disabled>', self.template)
        self.assertIn('<option value="private" selected>プライベート</option>', self.template)
        self.assertIn("syncSessionGroupVisibility", self.template)
        self.assertIn("visibility.value = 'group'", self.template)
        self.assertIn("グループなしでは「グループ内のみ」を選択できません", self.template)

    def test_empty_group_is_sent_as_null(self):
        self.assertIn("const selectedGroupId = document.getElementById('sessionGroup').value;", self.template)
        self.assertIn("group: selectedGroupId || null", self.template)

    def test_groupless_invite_candidates_are_loaded_from_friends(self):
        self.assertIn("/api/accounts/friends/", self.template)
        self.assertIn("フレンドを個別に招待できます", self.template)
        self.assertIn("招待できるフレンドがいません", self.template)

    def test_invite_candidate_names_are_rendered_as_text(self):
        self.assertIn("name.textContent = displayName;", self.template)
        self.assertNotIn("${member.user_detail.nickname || member.user_detail.username}", self.template)
