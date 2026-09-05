from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient

from accounts.character_models import GrowthRecord
from accounts.models import CharacterSheet, CharacterSheet6th, Group
from schedules import session_permissions
from schedules.models import SessionReward, TRPGSession


class RewardConcurrencyTest(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_simultaneous_applications_share_one_growth_record(self):
        owner = get_user_model().objects.create_user(username="reward-owner")
        player = get_user_model().objects.create_user(username="reward-player")
        group = Group.objects.create(name="報酬反映テスト", created_by=owner)
        session = TRPGSession.objects.create(title="同時反映", gm=owner, group=group)
        session_permissions.assign_session_gm(session, owner, granted_by=owner)
        participant = session_permissions.create_participant(session=session, user=player, role="player")
        character = CharacterSheet.objects.create(user=player, edition="6th")
        CharacterSheet6th.objects.create(character_sheet=character, name="探索者")
        participant.character_sheet = character
        participant.save(update_fields=["character_sheet"])
        reward = SessionReward.objects.create(participant=participant, created_by=owner, experience_points=7)
        barrier = Barrier(2)

        def apply_reward():
            try:
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute("SET lock_timeout = '5s'")
                client = APIClient()
                client.force_authenticate(user=owner)
                barrier.wait(timeout=10)
                response = client.post(f"/api/schedules/rewards/{reward.pk}/apply/", {}, format="json")
                return response.status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(apply_reward) for _ in range(2)]
            statuses = [future.result(timeout=20) for future in futures]

        self.assertEqual(statuses, [200, 200])
        reward.refresh_from_db()
        self.assertIsNotNone(reward.applied_growth_record_id)
        self.assertEqual(GrowthRecord.objects.filter(character_sheet=character).count(), 1)
        self.assertEqual(reward.applied_growth_record.experience_gained, 7)
