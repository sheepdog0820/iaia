from pathlib import Path

from django.test import SimpleTestCase


class ReleaseDocumentationTestCase(SimpleTestCase):
    ROOT = Path(__file__).resolve().parents[2]
    SECRET_PATTERNS = [
        'arkham' + '_admin_2024',
        'admin / ' + 'arkham' + '_admin_2024',
        'azathoth_gm / ' + 'arkham' + '2024',
        'Password: ' + 'arkham' + '_admin_2024',
        'パスワード: ' + 'arkham' + '_admin_2024',
    ]

    def test_readme_does_not_publish_test_account_passwords(self):
        content = (self.ROOT / 'README.md').read_text(encoding='utf-8')

        for value in self.SECRET_PATTERNS:
            self.assertNotIn(value, content)

        self.assertIn('### テストアカウント', content)
        self.assertIn('ローカル環境で作成してください。', content)
        self.assertIn('python create_admin.py', content)

    def test_release_documents_do_not_publish_fixed_admin_password(self):
        checked_paths = [
            'AGENTS.md',
            'CLAUDE.md',
            'SPECIFICATION.md',
            'SESSION_TEST_DATA_SPECIFICATION.md',
            'TEST_DATA_MANAGEMENT.md',
            'TEST_DATA_README.md',
            'accounts/views/dev_login_view.py',
            'create_admin.py',
            'schedules/management/commands/create_session_test_data.py',
            'schedules/management/commands/reset_dev_session_data.py',
            'server.sh',
            'templates/accounts/dev_login.html',
        ]

        for relative_path in checked_paths:
            content = (self.ROOT / relative_path).read_text(encoding='utf-8')
            for value in self.SECRET_PATTERNS:
                self.assertNotIn(value, content, f'{relative_path} publishes {value!r}')

    def test_django_version_is_documented_as_52_series(self):
        readme = (self.ROOT / 'README.md').read_text(encoding='utf-8')
        requirements = (self.ROOT / 'requirements.txt').read_text(encoding='utf-8')

        self.assertIn('Django 5.2', readme)
        self.assertIn('Django>=5.2.0,<5.3', requirements)
        self.assertNotIn('Django ' + '4.2+', readme)
        self.assertNotIn('Django>=' + '4.2.0,<5.0', requirements)
