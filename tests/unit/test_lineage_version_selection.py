from types import SimpleNamespace

from django.test import SimpleTestCase

from accounts.services.character_version_service import CharacterVersionService


class LineageVersionSelectionTests(SimpleTestCase):
    def test_latest_version_excludes_other_roots_and_includes_branches(self):
        records = [
            SimpleNamespace(pk=1, parent_data_id=None, version=1),
            SimpleNamespace(pk=2, parent_data_id=1, version=4),
            SimpleNamespace(pk=3, parent_data_id=2, version=7),
            SimpleNamespace(pk=4, parent_data_id=1, version=9),
            SimpleNamespace(pk=5, parent_data_id=None, version=100),
            SimpleNamespace(pk=6, parent_data_id=5, version=200),
        ]
        self.assertEqual(CharacterVersionService._latest_version_for_root(records, 1), 9)
        self.assertEqual(CharacterVersionService._latest_version_for_root(records, 5), 200)

    def test_unrelated_roots_do_not_require_quadratic_record_scans(self):
        visits = []

        class Record:
            parent_data_id = None
            version = 1

            def __init__(self, key):
                self.key = key

            @property
            def pk(self):
                visits.append(self.key)
                return self.key

        records = [Record(key) for key in range(1000)]
        self.assertEqual(CharacterVersionService._latest_version_for_root(records, 0), 1)
        self.assertLessEqual(len(visits), 4 * len(records))
