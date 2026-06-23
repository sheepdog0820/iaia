import subprocess
from pathlib import Path

from django.test import SimpleTestCase


class RepositoryHygieneTests(SimpleTestCase):
    ROOT = Path(__file__).resolve().parents[2]

    def git_ls_files(self):
        result = subprocess.run(
            ['git', 'ls-files', '--cached'],
            cwd=self.ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def test_dangerous_generated_paths_are_not_tracked(self):
        allowed_env_examples = {
            '.env.aws-prod-oauth.example',
            '.env.compose.example',
            '.env.development.example',
            '.env.docker.example',
            '.env.example',
            '.env.local-oauth.example',
            '.env.production.example',
            '.env.staging.example',
        }
        forbidden = []

        for path in self.git_ls_files():
            parts = path.split('/')
            filename = parts[-1]
            if path.startswith('.env') and path not in allowed_env_examples:
                forbidden.append(path)
            elif parts[0] in {'node_modules', 'media', 'staticfiles', 'logs'}:
                forbidden.append(path)
            elif parts[0].startswith('venv') or parts[0] == '.venv':
                forbidden.append(path)
            elif filename in {'cookies.txt', 'db.sqlite3', 'db.sqlite3-journal'}:
                forbidden.append(path)
            elif parts[0] in {'test-results', 'playwright-report', 'traces'}:
                forbidden.append(path)
            elif path.startswith('tests/results/') and path != 'tests/results/README.md':
                forbidden.append(path)

        self.assertEqual(forbidden, [])

    def test_hygiene_filter_treats_generated_names_as_path_segments(self):
        tracked_paths = set(self.git_ls_files())

        self.assertIn('schedules/test_session_notes_logs.py', tracked_paths)
        self.assertIn('scripts/aws/sync_media.py', tracked_paths)

        forbidden_segments = {'node_modules', 'media', 'staticfiles', 'logs'}
        false_positive_candidates = [
            'schedules/test_session_notes_logs.py',
            'scripts/aws/sync_media.py',
        ]
        for path in false_positive_candidates:
            parts = set(path.split('/'))
            self.assertTrue(parts.isdisjoint(forbidden_segments))

    def test_ignore_files_cover_generated_artifacts(self):
        gitignore = (self.ROOT / '.gitignore').read_text(encoding='utf-8')
        dockerignore = (self.ROOT / '.dockerignore').read_text(encoding='utf-8')

        required_gitignore_entries = [
            '.env*',
            '!.env*.example',
            'venv*/',
            'node_modules/',
            'cookies.txt',
            'staticfiles/',
            'media/',
            'logs/',
            'test-results/',
            'playwright-report/',
        ]
        required_dockerignore_entries = [
            '.env',
            '.env.*',
            '!.env.example',
            '!.env.*.example',
            'venv*/',
            'node_modules/',
            'cookies.txt',
            '/staticfiles/',
            '/media/',
            'test-results/',
            'playwright-report/',
        ]

        for entry in required_gitignore_entries:
            self.assertIn(entry, gitignore)
        for entry in required_dockerignore_entries:
            self.assertIn(entry, dockerignore)

    def test_ci_support_files_are_trackable(self):
        required_paths = [
            '.env.compose.example',
            '.env.docker.example',
            '.github/workflows/django-ci.yml',
            '.python-version',
        ]

        for path in required_paths:
            with self.subTest(path=path):
                self.assertTrue((self.ROOT / path).exists())
                result = subprocess.run(
                    ['git', 'check-ignore', '-q', path],
                    cwd=self.ROOT,
                    check=False,
                )
                self.assertEqual(result.returncode, 1)
