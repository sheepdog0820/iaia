from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.core.management import call_command
from django.test import SimpleTestCase


class OpenAPISchemaTestCase(SimpleTestCase):
    def test_spectacular_schema_generates_without_warnings(self):
        stdout = StringIO()
        stderr = StringIO()
        with NamedTemporaryFile(suffix='.yaml', delete=False) as schema_file:
            schema_path = Path(schema_file.name)
        try:
            call_command(
                'spectacular',
                file=str(schema_path),
                validate=True,
                stdout=stdout,
                stderr=stderr,
            )
        finally:
            schema_path.unlink(missing_ok=True)

        combined_output = f'{stdout.getvalue()}\n{stderr.getvalue()}'
        self.assertNotIn('Warning', combined_output)
        self.assertNotIn('Error', combined_output)
