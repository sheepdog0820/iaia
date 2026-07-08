import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class CharacterCreateUiStaticTests(SimpleTestCase):
    SEVENTH_ONLY_SKILL_LABELS = ["鑑定", "手さばき", "サバイバル", "魅惑", "威圧"]

    def read_text(self, relative_path):
        return (Path(settings.BASE_DIR) / relative_path).read_text(encoding="utf-8")

    def extract_bracket_block(self, text, marker):
        start = text.index(marker)
        bracket = text.index("[", start)
        depth = 0

        for index in range(bracket, len(text)):
            if text[index] == "[":
                depth += 1
            elif text[index] == "]":
                depth -= 1
                if depth == 0:
                    return text[bracket : index + 1]

        raise AssertionError(f"Unclosed bracket block for {marker}")

    def extract_js_skill_names(self, text, marker):
        block = self.extract_bracket_block(text, marker)
        return set(re.findall(r"name:\s*'([^']+)'", block))

    def extract_ordered_js_skill_names(self, text, marker):
        block = self.extract_bracket_block(text, marker)
        return re.findall(r"name:\s*'([^']+)'", block)

    def extract_function_block(self, text, marker, next_marker):
        start = text.index(marker)
        end = text.index(next_marker, start)
        return text[start:end]

    def extract_between(self, text, start_marker, end_marker):
        start = text.index(start_marker)
        end = text.index(end_marker, start)
        return text[start:end]

    def extract_python_skill_names(self, text, marker):
        block = self.extract_bracket_block(text, marker)
        return {match[0] or match[1] for match in re.findall(r"'([^']+)'|\"([^\"]+)\"", block)}

    def test_6th_default_skills_do_not_include_7th_only_skills(self):
        script = self.read_text("static/accounts/js/character6th.js")

        for skill_label in self.SEVENTH_ONLY_SKILL_LABELS:
            self.assertNotIn(f'name: "{skill_label}"', script)

        for skill_key in ["appraise", "sleight_of_hand", "survival", "charm", "intimidate"]:
            self.assertNotIn(f'"{skill_key}"', script)

    def test_6th_create_labels_use_custom_and_status_roll_copy(self):
        template = self.read_text("templates/accounts/character_6th_create.html")

        self.assertNotIn("表示/非表示", template)
        self.assertIn("表示項目カスタム", template)
        self.assertIn("能力値ロール", template)

    def test_character_create_basic_info_uses_memo_and_secret_ho_fields(self):
        for relative_path in [
            "templates/accounts/character_6th_create.html",
            "templates/accounts/character_7th_create.html",
        ]:
            with self.subTest(relative_path=relative_path):
                template = self.read_text(relative_path)

                self.assertIn('<label for="traits_mannerisms" class="form-label">メモ</label>', template)
                self.assertIn('name="secret_ho_info"', template)
                self.assertIn("秘匿HO情報", template)

    def test_character_create_templates_have_bulk_image_modal_and_edit_preview_slots(self):
        for relative_path in [
            "templates/accounts/character_6th_create.html",
            "templates/accounts/character_7th_create.html",
        ]:
            with self.subTest(relative_path=relative_path):
                template = self.read_text(relative_path)

                for marker in [
                    'id="characterImageUploadModal"',
                    'id="character-image-drop-zone"',
                    'id="character-image-select-btn"',
                    'id="character-image-modal-list"',
                    'id="image-existing-view"',
                    'id="image-selected-view"',
                    'id="image-preview-list"',
                    'data-bs-target="#characterImageUploadModal"',
                ]:
                    self.assertIn(marker, template)

    def test_character_create_image_js_supports_drop_modal_and_existing_image_switcher(self):
        for relative_path in [
            "static/accounts/js/character6th.js",
            "static/accounts/js/character7th.js",
        ]:
            with self.subTest(relative_path=relative_path):
                script = self.read_text(relative_path)

                for marker in [
                    "new DataTransfer()",
                    "document.getElementById('character-image-drop-zone')",
                    "document.getElementById('character-image-modal-list')",
                    "'dragover'",
                    "dropZone?.addEventListener('drop'",
                    "fetchJson(`/api/accounts/character-sheets/${editCharacterId}/images/`)",
                    "character-edit-image-switcher",
                    "character-edit-thumbnail-button",
                    "renderExistingImages",
                ]:
                    self.assertIn(marker, script)

    def test_character_detail_reference_background_is_pdf_backstory_only(self):
        template = self.read_text("templates/accounts/character_detail.html")
        basic_block = self.extract_function_block(template, "function displayBasicInfo(character)", "// 複数画像表示")
        background_block = self.extract_function_block(
            template, "function displayBackgroundInfo(character)", "// 装備表示"
        )

        self.assertIn("{ label: 'メモ'", basic_block)
        self.assertIn("{ label: '秘匿HO情報'", basic_block)

        for label in [
            "容姿の描写",
            "イデオロギー／信念",
            "重要な人々",
            "意味のある場所",
            "秘蔵の品",
            "負傷、傷跡",
            "恐怖症、マニア",
            "魔道書、呪文、アーティファクト",
            "遭遇した超自然の存在",
        ]:
            self.assertIn(label, background_block)

        self.assertNotIn("{ label: '特徴'", background_block)
        self.assertNotIn("{ label: 'メモ'", background_block)
        self.assertNotIn("personal_history", background_block)
        self.assertNotIn("important_events", background_block)
        self.assertNotIn("fellow_investigators", background_block)

    def test_6th_and_7th_background_form_fields_match(self):
        expected_names = [
            "appearance",
            "ideals",
            "bonds",
            "meaningful_locations",
            "items",
            "scars_injuries",
            "flaws",
            "arcane_tomes_spells_artifacts",
            "encounters_with_strange_entities",
        ]

        for relative_path in [
            "templates/accounts/character_6th_create.html",
            "templates/accounts/character_7th_create.html",
        ]:
            with self.subTest(relative_path=relative_path):
                template = self.read_text(relative_path)
                background_block = self.extract_between(
                    template,
                    "<!-- 背景情報タブ -->",
                    "<!-- 職業テンプレートモーダル -->",
                )

                names = re.findall(r'<textarea[^>]+name="([^"]+)"', background_block)
                self.assertEqual(expected_names, names)

    def test_character_detail_background_section_label_is_current(self):
        template = self.read_text("templates/accounts/character_detail.html")

        self.assertIn('<i class="fas fa-book-open"></i> 背景情報', template)
        self.assertNotIn("背景・特徴", template)

    def test_6th_and_7th_background_js_fields_match(self):
        expected_load_ids = [
            "traits_mannerisms",
            "appearance",
            "ideals",
            "bonds",
            "meaningful_locations",
            "items",
            "scars_injuries",
            "flaws",
            "arcane_tomes_spells_artifacts",
            "encounters_with_strange_entities",
        ]
        expected_payload_keys = [
            "traits_mannerisms",
            "appearance_description",
            "beliefs_ideology",
            "significant_people",
            "meaningful_locations",
            "treasured_possessions",
            "scars_injuries",
            "phobias_manias",
            "arcane_tomes_spells_artifacts",
            "encounters_with_strange_entities",
        ]

        for relative_path in [
            "static/accounts/js/character6th.js",
            "static/accounts/js/character7th.js",
        ]:
            with self.subTest(relative_path=relative_path):
                script = self.read_text(relative_path)
                load_ids = re.findall(r"setValueById\('([^']+)', backgroundInfo\.[^)]+\);", script)
                payload_match = re.search(r"const backgroundData = \{(?P<body>.*?)\n        \};", script, re.S)
                self.assertIsNotNone(payload_match)
                payload_keys = re.findall(r"^            ([a-z_]+):", payload_match.group("body"), re.M)

                self.assertEqual(expected_load_ids, load_ids)
                self.assertEqual(expected_payload_keys, payload_keys)

    def test_character_detail_long_memo_uses_full_width_scrollable_block(self):
        template = self.read_text("templates/accounts/character_detail.html")
        basic_block = self.extract_function_block(template, "function displayBasicInfo(character)", "// 複数画像表示")

        self.assertIn("{ label: 'メモ', value: getDisplayMemo(background), type: 'longText' }", basic_block)
        self.assertIn("type: 'longText'", basic_block)
        self.assertIn("col-12 mb-3 basic-info-long-item", basic_block)
        self.assertIn("basic-info-long-body", basic_block)
        self.assertIn("max-height: 28rem;", template)
        self.assertIn("overflow-y: auto;", template)
        self.assertIn("max-height: 22rem;", template)

    def test_character_detail_mobile_tabs_are_horizontally_scrollable(self):
        template = self.read_text("templates/accounts/character_detail.html")

        self.assertIn("#equipmentTabs,", template)
        self.assertIn("#historyTabs {", template)
        self.assertIn("overflow-x: auto;", template)
        self.assertIn("flex-wrap: nowrap;", template)
        self.assertIn("white-space: nowrap;", template)

    def test_character_detail_has_no_legacy_7th_background_block(self):
        template = self.read_text("templates/accounts/character_detail.html")
        edition_block = self.extract_function_block(
            template,
            "function displayEditionSpecific(character)",
            "// バージョン履歴読み込み",
        )

        for legacy_label in [
            "7版固有情報",
            "個人的な記述",
            "思想・信念",
            "大切な所持品",
            "特性",
            "負傷・傷跡",
        ]:
            self.assertNotIn(legacy_label, edition_block)

        self.assertIn("container.innerHTML = '';", edition_block)

    def test_character_list_primary_actions_include_direct_link_copy(self):
        template = self.read_text("templates/accounts/character_list.html")
        action_block = self.extract_between(
            template,
            '<div class="character-card-actions" role="group" aria-label="キャラクター操作">',
            '<div class="dropdown character-card-more">',
        )

        self.assertIn('href="/accounts/character/${character.id}/"', action_block)
        self.assertIn(
            "href=\"/accounts/character/create/${character.edition || '6th'}/?id=${character.id}\"",
            action_block,
        )
        self.assertIn('onclick="copyCharacterUrl(${character.id})"', action_block)
        self.assertIn("リンクコピー", action_block)
        self.assertNotIn('dropdown-item" onclick="copyCharacterUrl', template)

    def test_character_list_dark_mode_styles_keep_cards_readable(self):
        stylesheet = self.read_text("static/accounts/css/character_list.css")

        for marker in [
            "@media (prefers-color-scheme: dark)",
            ".character-list .character-card .card-title,",
            ".character-list .character-meta strong,",
            ".character-list .character-stat-value",
            "color: #f8fafc !important;",
            "color: #cbd5e1 !important;",
            ".character-list .btn-outline-character-copy",
        ]:
            self.assertIn(marker, stylesheet)

    def test_character_list_share_copy_uses_fixed_token_url(self):
        template = self.read_text("templates/accounts/character_list.html")

        self.assertIn("axios.post('/api/share-links/fixed-url/'", template)
        self.assertIn("resource_type: 'character'", template)
        self.assertIn("auto_enable_link: true", template)
        self.assertIn("response.data.share_url", template)
        self.assertNotIn("/characters/${character.id}/view/", template)
        self.assertNotIn("/characters/${characterId}/view/", template)

    def test_scenario_archive_direct_link_uses_fixed_token_url(self):
        template = self.read_text("templates/scenarios/archive.html")

        self.assertIn("copyScenarioPublicUrl(${scenario.id})", template)
        self.assertIn("openScenarioShareView(${scenario.id})", template)
        self.assertIn("直接リンクをコピー", template)
        self.assertIn("直接リンクを開く", template)
        self.assertIn("シナリオ直接リンクをコピーしました。", template)
        self.assertIn("axios.post('/api/share-links/fixed-url/'", template)
        self.assertIn("resource_type: 'scenario'", template)
        self.assertIn("auto_enable_link: true", template)
        self.assertIn("response.data.share_url", template)
        self.assertNotIn("/scenarios/${scenario.id}/view/", template)
        self.assertNotIn("/scenarios/${scenarioId}/view/", template)

    def test_scenario_archive_edit_controls_are_owner_only(self):
        template = self.read_text("templates/scenarios/archive.html")

        self.assertIn("const recommendedSkillEditHtml = canManage ?", template)
        self.assertIn("const imageUploadControlsHtml = canManage ?", template)
        self.assertIn("${recommendedSkillEditHtml}", template)
        self.assertIn("${imageUploadControlsHtml}", template)
        self.assertIn("const scenarioShareControlsHtml = canManage ?", template)

    def test_ccfolia_default_skills_are_split_by_edition(self):
        template = self.read_text("templates/schedules/session_detail.html")

        sixth_names = self.extract_js_skill_names(template, "const CCFOLIA_COC6_DEFAULT_SKILLS")
        seventh_names = self.extract_js_skill_names(template, "const CCFOLIA_COC7_DEFAULT_SKILLS")

        for skill_label in self.SEVENTH_ONLY_SKILL_LABELS:
            self.assertNotIn(skill_label, sixth_names)
            self.assertIn(skill_label, seventh_names)

        self.assertEqual(60, len(sixth_names))
        self.assertEqual(65, len(seventh_names))
        self.assertIn(
            "const defaultSkills = edition === '7th' ? CCFOLIA_COC7_DEFAULT_SKILLS : CCFOLIA_COC6_DEFAULT_SKILLS;",
            template,
        )

    def test_ccfolia_skill_output_preserves_skill_tab_order(self):
        template = self.read_text("templates/schedules/session_detail.html")

        sixth_names = self.extract_ordered_js_skill_names(template, "const CCFOLIA_COC6_DEFAULT_SKILLS")
        seventh_names = self.extract_ordered_js_skill_names(template, "const CCFOLIA_COC7_DEFAULT_SKILLS")

        expected_combat_order = [
            "回避",
            "キック",
            "組み付き",
            "こぶし（パンチ）",
            "頭突き",
            "投擲",
            "マーシャルアーツ",
            "拳銃",
            "サブマシンガン",
            "ショットガン",
            "マシンガン",
            "ライフル",
        ]
        self.assertEqual(expected_combat_order, sixth_names[:12])
        self.assertEqual(expected_combat_order, seventh_names[:12])

        for names in [sixth_names, seventh_names]:
            self.assertLess(names.index("目星"), names.index("運転"))
            self.assertLess(names.index("変装"), names.index("言いくるめ"))
            self.assertLess(names.index("母国語"), names.index("医学"))

        self.assertIn("const skillValues = new Map();", template)
        self.assertIn("const customSkills = new Map();", template)
        self.assertNotIn(".sort((a, b) => a.skill_name.localeCompare", template)

    def test_character_view_skill_lists_are_split_by_edition(self):
        for relative_path in ["accounts/views/character_views.py"]:
            with self.subTest(relative_path=relative_path):
                source = self.read_text(relative_path)

                sixth_names = self.extract_python_skill_names(source, "COC6_BASIC_SKILL_NAMES")
                seventh_names = self.extract_python_skill_names(source, "COC7_BASIC_SKILL_NAMES")

                for skill_label in self.SEVENTH_ONLY_SKILL_LABELS:
                    self.assertNotIn(skill_label, sixth_names)
                    self.assertIn(skill_label, seventh_names)

                self.assertEqual(60, len(sixth_names))
                self.assertEqual(65, len(seventh_names))
                self.assertNotIn("common_skills = [", source)
