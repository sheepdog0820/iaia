from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ParticipantRoleMigrationTests(TransactionTestCase):
    before = ("schedules", "0054_sessionrecruitmentlink_sessionrecruitmentlinkuse_and_more")
    after = ("schedules", "0055_allow_multiple_participant_roles")

    def setUp(self):
        self.latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(self.restore_latest_schema)
        apps = self.migrate(self.before)
        session = apps.get_model("schedules", "TRPGSession").objects.create(title="移行検証専用")
        participant = apps.get_model("schedules", "SessionParticipant").objects.create(
            session_id=session.pk, guest_name="移行検証ゲスト"
        )
        self.participant_id = participant.pk
        role = apps.get_model("schedules", "SessionParticipantRole").objects.create(
            participant_id=participant.pk, role="player"
        )
        self.role_id = role.pk

    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        return executor.loader.project_state([target]).apps

    def restore_latest_schema(self):
        MigrationExecutor(connection).migrate(self.latest)

    def test_forward_and_reverse_preserve_single_role(self):
        for target in (self.after, self.before):
            with self.subTest(target=target):
                apps = self.migrate(target)
                role = apps.get_model("schedules", "SessionParticipantRole").objects.get(pk=self.role_id)
                self.assertEqual((role.participant_id, role.role), (self.participant_id, "player"))

    def test_multiple_roles_block_reverse_without_losing_data(self):
        apps = self.migrate(self.after)
        roles = apps.get_model("schedules", "SessionParticipantRole")
        roles.objects.create(participant_id=self.participant_id, role="gm")
        with self.assertRaises(IntegrityError), transaction.atomic():
            roles.objects.create(participant_id=self.participant_id, role="gm")

        with self.assertRaises(IntegrityError):
            self.migrate(self.before)

        self.assertEqual(
            set(roles.objects.filter(participant_id=self.participant_id).values_list("role", flat=True)),
            {"player", "gm"},
        )
        self.assertIn(self.after, MigrationExecutor(connection).loader.applied_migrations)
