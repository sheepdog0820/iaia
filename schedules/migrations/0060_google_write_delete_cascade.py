from django.db import migrations

_REFERENCES = [
    ("schedules_googlewriteadmission", "job_id", "schedules_asyncjob"),
    ("schedules_googlewritereservation", "admission_id", "schedules_googlewriteadmission"),
]
_SQLITE_TRIGGERS = [
    (
        "CREATE TRIGGER google_write_job_id_delete AFTER DELETE ON schedules_asyncjob "
        "BEGIN DELETE FROM schedules_googlewriteadmission WHERE job_id = OLD.id; END",
        "DROP TRIGGER google_write_job_id_delete",
    ),
    (
        "CREATE TRIGGER google_write_admission_id_delete AFTER DELETE ON schedules_googlewriteadmission "
        "BEGIN DELETE FROM schedules_googlewritereservation WHERE admission_id = OLD.id; END",
        "DROP TRIGGER google_write_admission_id_delete",
    ),
]


def _postgres_fk(schema_editor, table_name, column_name, parent_name, cascade):
    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(cursor, table_name)
    matches = [
        name
        for name, data in constraints.items()
        if data["foreign_key"] == (parent_name, "id") and data["columns"] == [column_name]
    ]
    if len(matches) != 1:
        raise RuntimeError("Google受付の参照制約を確認できません。")
    quote = schema_editor.quote_name
    table, column, parent, constraint = map(quote, [table_name, column_name, parent_name, matches[0]])
    schema_editor.execute(f"ALTER TABLE {table} DROP CONSTRAINT {constraint}")
    clause = "ON DELETE CASCADE " if cascade else ""
    schema_editor.execute(
        f"ALTER TABLE {table} ADD CONSTRAINT {constraint} FOREIGN KEY ({column}) "
        f"REFERENCES {parent} ({quote('id')}) {clause}DEFERRABLE INITIALLY DEFERRED"
    )


def install_delete_cascade(apps, schema_editor):
    """An old ORM must erase encrypted admissions when deleting its known jobs."""
    if schema_editor.connection.vendor == "sqlite":
        for create_sql, _ in _SQLITE_TRIGGERS:
            schema_editor.execute(create_sql)
    elif schema_editor.connection.vendor == "postgresql":
        for table, column, parent in _REFERENCES:
            _postgres_fk(schema_editor, table, column, parent, True)
    else:
        raise RuntimeError("Google受付はSQLiteまたはPostgreSQLのDBを使用してください。")


def remove_delete_cascade(apps, schema_editor):
    if schema_editor.connection.vendor == "sqlite":
        for _, drop_sql in reversed(_SQLITE_TRIGGERS):
            schema_editor.execute(drop_sql)
    elif schema_editor.connection.vendor == "postgresql":
        for table, column, parent in reversed(_REFERENCES):
            _postgres_fk(schema_editor, table, column, parent, False)
    else:
        raise RuntimeError("Google受付はSQLiteまたはPostgreSQLのDBを使用してください。")


class Migration(migrations.Migration):
    dependencies = [("schedules", "0059_google_write_admission")]
    operations = [migrations.RunPython(install_delete_cascade, remove_delete_cascade)]
