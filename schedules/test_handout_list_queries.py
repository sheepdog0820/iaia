from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.character_models import CharacterSheet, CharacterSheet6th, CharacterSheet7th
from schedules import session_permissions
from schedules.models import HandoutInfo, TRPGSession


class HandoutListQueryTests(APITestCase):
    def test_list_queries_do_not_grow_with_handout_count(self):
        users = get_user_model()
        gm = users.objects.create_user(username="list_query_gm")
        session = TRPGSession.objects.create(title="一覧検証", gm=gm, date=timezone.now())
        participants = []
        for index, (edition, model) in enumerate((("6th", CharacterSheet6th), ("7th", CharacterSheet7th))):
            player = users.objects.create_user(username=f"list_query_player_{index}")
            sheet = CharacterSheet.objects.create(user=player, edition=edition)
            model.objects.create(character_sheet=sheet, name=f"探索者{index}", int_value=10, edu_value=10)
            participant = session_permissions.create_participant(session=session, user=player, role="player")
            participant.character_sheet = sheet
            participant.save(update_fields=["character_sheet"])
            participants.append(participant)
        handouts = []
        self.client.force_authenticate(gm)
        query_counts = []
        for size in (1, 20):
            while len(handouts) < size:
                number = len(handouts)
                handouts.append(
                    HandoutInfo.objects.create(
                        session=session,
                        participant=participants[number % 2],
                        title=f"個別情報{number}",
                        content=f"秘匿本文{number}",
                        is_secret=True,
                    )
                )
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get("/api/schedules/handouts/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], size)
            self.assertEqual({row["id"] for row in response.data["results"]}, {h.pk for h in handouts})
            for row in response.data["results"]:
                participant = row["participant_detail"]
                self.assertIn(participant["character_sheet_detail"]["name"], ("探索者0", "探索者1"))
                self.assertIn("player", participant["roles"])
            query_counts.append(len(queries))
        self.assertLessEqual(query_counts[1], query_counts[0] + 2, query_counts)
