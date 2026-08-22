from pathlib import Path

from django.test import SimpleTestCase


class ScreenActionUiStaticTests(SimpleTestCase):
    def read_text(self, path):
        return Path(path).read_text(encoding="utf-8")

    def test_shared_mobile_action_assets_prioritize_content_space_and_touch_targets(self):
        stylesheet = self.read_text("static/css/screen-actions.css")
        script = self.read_text("static/js/screen-actions.js")

        self.assertIn("@media (max-width: 767.98px)", stylesheet)
        self.assertIn("min-height: 44px", stylesheet)
        self.assertIn("env(safe-area-inset-bottom)", stylesheet)
        self.assertIn(".screen-action-sheet", stylesheet)
        self.assertIn(".screen-action-primary", stylesheet)
        self.assertIn("screen-actions-open", script)
        self.assertIn("event.key === 'Escape'", script)
        self.assertIn("has-screen-primary-action", script)

    def test_character_detail_uses_back_local_primary_and_mobile_more_groups(self):
        template = self.read_text("templates/accounts/character_detail.html")

        self.assertIn("data-screen-actions-page", template)
        self.assertIn("data-screen-actions", template)
        self.assertIn("screen-action-back", template)
        self.assertIn("data-screen-action-sheet", template)
        self.assertIn("data-screen-actions-toggle", template)
        self.assertIn("screen-action-primary", template)
        self.assertIn("キャラクター一覧へ", template)

    def test_character_create_screens_keep_only_save_in_the_fixed_footer(self):
        for path in [
            "templates/accounts/character_6th_create.html",
            "templates/accounts/character_7th_create.html",
        ]:
            with self.subTest(path=path):
                template = self.read_text(path)
                self.assertIn("data-screen-actions-page", template)
                self.assertIn("data-screen-action-sheet", template)
                self.assertIn("screen-form-primary", template)
                self.assertIn('id="footerSaveCharacter"', template)
                self.assertIn("保存して詳細へ", template)
                footer = template.split("<!-- 固定フッター -->", 1)[1]
                self.assertNotIn('id="footerResetSkills"', footer)
                self.assertNotIn('id="footerCreateVersion"', footer)

    def test_session_detail_prioritizes_one_primary_action_and_mobile_action_sheet(self):
        template = self.read_text("templates/schedules/session_detail.html")

        self.assertIn("data-screen-actions-page", template)
        self.assertIn("screen-action-back", template)
        self.assertIn("data-screen-action-sheet", template)
        self.assertIn("screen-action-primary", template)
        self.assertIn("data-screen-actions-toggle", template)
        self.assertIn("セッション一覧へ", template)

    def test_session_edit_form_exposes_title_input_on_detail_and_list_screens(self):
        form_fields = self.read_text("templates/schedules/_session_edit_form_fields.html")
        detail_template = self.read_text("templates/schedules/session_detail.html")
        list_template = self.read_text("templates/schedules/sessions.html")

        title_control = form_fields.split("セッションタイトル", 1)[1].split("<input", 1)[1].split(">", 1)[0]
        self.assertIn('type="text"', title_control)
        self.assertNotIn('type="hidden"', title_control)
        self.assertIn("_session_edit_form_fields.html", detail_template)
        self.assertIn("_session_edit_form_fields.html", list_template)
        self.assertIn("document.getElementById('editSessionTitle').value", detail_template)
        self.assertIn("document.getElementById('editSessionTitle').value", list_template)

    def test_scenario_detail_separates_primary_local_and_danger_actions(self):
        template = self.read_text("templates/scenarios/archive.html")

        self.assertIn('class="container" data-screen-actions-page', template)
        self.assertIn("modal-fullscreen-sm-down", template)
        self.assertIn("scenario-detail-primary-actions", template)
        self.assertIn("scenario-detail-local-actions", template)
        self.assertIn("scenario-detail-danger-actions", template)

    def test_compact_action_layout_covers_tablet_and_narrow_desktop_widths(self):
        stylesheet = self.read_text("static/css/screen-actions.css")

        self.assertIn("@media (max-width: 1399.98px)", stylesheet)
        self.assertIn("translateX(105%)", stylesheet)
        self.assertIn("grid-template-columns: auto minmax(0, 1fr) auto auto", stylesheet)

    def test_each_screen_has_mobile_width_and_touch_target_adjustments(self):
        stylesheet = self.read_text("static/css/screen-actions.css")
        scenario_template = self.read_text("templates/scenarios/archive.html")

        self.assertIn("[data-screen-actions-page].container", stylesheet)
        self.assertIn(".character-creator #mainTabs", stylesheet)
        self.assertIn(".character-detail #equipmentTabs .nav-link", stylesheet)
        self.assertIn(".session-main-column > .card .card-body", stylesheet)
        self.assertIn("scroll-snap-type: x proximity", stylesheet)
        self.assertIn(".scenario-direct-link-control .input-group", scenario_template)
        self.assertIn("min-height: 44px", scenario_template)
