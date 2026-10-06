from django.db import migrations


def _replace_postgres_fk(schema_editor, cascade):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, "schedules_googlejobdispatch")
    matches = [
        name
        for name, data in constraints.items()
        if data["foreign_key"] == ("schedules_asyncjob", "id") and data["columns"] == ["job_id"]
    ]
    if len(matches) != 1:
        raise RuntimeError("Google配送の参照制約を確認できません。")
    quote = schema_editor.quote_name
    table, constraint = quote("schedules_googlejobdispatch"), quote(matches[0])
    schema_editor.execute(f"ALTER TABLE {table} DROP CONSTRAINT {constraint}")
    delete_clause = "ON DELETE CASCADE " if cascade else ""
    schema_editor.execute(
        f"ALTER TABLE {table} ADD CONSTRAINT {constraint} FOREIGN KEY ({quote('job_id')}) "
        f"REFERENCES {quote('schedules_asyncjob')} ({quote('id')}) {delete_clause}DEFERRABLE INITIALLY DEFERRED"
    )


def install_delete_cascade(apps, schema_editor):
    """Keep deletion safe when rolling application code back, keeping this schema."""
    if schema_editor.connection.vendor == "sqlite":
        schema_editor.execute(
            "CREATE TRIGGER google_dispatch_job_delete AFTER DELETE ON schedules_asyncjob "
            "BEGIN DELETE FROM schedules_googlejobdispatch WHERE job_id = OLD.id; END"
        )
    elif schema_editor.connection.vendor == "postgresql":
        _replace_postgres_fk(schema_editor, True)
    else:
        raise RuntimeError("Google配送はSQLiteまたはPostgreSQLのDBを使用してください。")


def remove_delete_cascade(apps, schema_editor):
    if schema_editor.connection.vendor == "sqlite":
        schema_editor.execute("DROP TRIGGER google_dispatch_job_delete")
    elif schema_editor.connection.vendor == "postgresql":
        _replace_postgres_fk(schema_editor, False)
    else:
        raise RuntimeError("Google配送はSQLiteまたはPostgreSQLのDBを使用してください。")


class Migration(migrations.Migration):
    dependencies = [("schedules", "0057_google_job_dispatch")]
    operations = [migrations.RunPython(install_delete_cascade, remove_delete_cascade)]
