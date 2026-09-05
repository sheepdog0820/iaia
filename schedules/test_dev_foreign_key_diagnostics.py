from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from django.core.management import CommandError
from django.db.utils import ConnectionHandler

from schedules.management.commands import reset_dev_session_data


class DevelopmentForeignKeyDiagnosticsTest(TestCase):
    def setUp(self):
        self.db = ConnectionHandler({"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}})[
            "default"
        ]
        self.addCleanup(self.db.close)
        self.command = reset_dev_session_data.Command(stdout=StringIO())
        connection_patch = patch.object(reset_dev_session_data, "connection", self.db)
        connection_patch.start()
        self.addCleanup(connection_patch.stop)
        with self.db.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys=OFF")
            cursor.execute("CREATE TABLE parent (id TEXT PRIMARY KEY)")

    def test_valid_foreign_keys_are_silent(self):
        with self.db.cursor() as cursor:
            cursor.execute("CREATE TABLE child (id INTEGER PRIMARY KEY, ref TEXT REFERENCES parent(id))")
            cursor.execute("INSERT INTO parent VALUES ('valid')")
            cursor.execute("INSERT INTO child VALUES (1, 'valid')")
        self.command._assert_foreign_keys_ok()
        self.assertEqual(self.command.stdout.getvalue(), "")

    def test_quoted_identifiers_report_constraint_failure_without_sql_error(self):
        with self.db.cursor() as cursor:
            cursor.execute(
                'CREATE TABLE "child""table" (id INTEGER PRIMARY KEY, "ref""column" TEXT REFERENCES parent(id))'
            )
            cursor.execute('INSERT INTO "child""table" VALUES (1, \'missing\')')
        with self.assertRaises(CommandError):
            self.command._assert_foreign_keys_ok()
        self.assertIn('child"table rowid=1 -> parent fk_id=0', self.command.stdout.getvalue())
        with self.db.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM "child""table"')
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_without_rowid_tables_report_failure_without_selecting_rowid(self):
        with self.db.cursor() as cursor:
            cursor.execute("CREATE TABLE child (id TEXT PRIMARY KEY, ref TEXT REFERENCES parent(id)) WITHOUT ROWID")
            cursor.execute("INSERT INTO child VALUES ('child-key', 'missing')")
        with self.assertRaises(CommandError):
            self.command._assert_foreign_keys_ok()
        self.assertIn("child rowid=None -> parent fk_id=0", self.command.stdout.getvalue())
