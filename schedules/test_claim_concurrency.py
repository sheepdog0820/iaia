from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from accounts.models import Group, GroupMembership
from schedules.models import ParticipantClaimRequest, ParticipantIdentity, SessionParticipant, TRPGSession
from schedules.participant_claims import ClaimRequestError, approve_claim_request, reject_claim_request


class ClaimConcurrencyTest(TransactionTestCase):
    def check_competing_approvals(self, with_identity):
        owner = get_user_model().objects.create_user(username="claim-owner")
        users = [get_user_model().objects.create_user(username=f"claim-user-{n}") for n in range(2)]
        group = Group.objects.create(name="紐付け試験", created_by=owner)
        identity = ParticipantIdentity.objects.create(group=group, display_name="ゲスト") if with_identity else None
        session = TRPGSession.objects.create(title="紐付け試験", gm=owner, group=group)
        participant = SessionParticipant.objects.create(
            session=session, guest_name="ゲスト", participant_identity=identity
        )
        participants = [participant]
        if identity:
            other_session = TRPGSession.objects.create(title="別のセッション", gm=owner, group=group)
            participants.append(
                SessionParticipant.objects.create(
                    session=other_session, guest_name="同じゲスト", participant_identity=identity
                )
            )
        claims = [
            ParticipantClaimRequest.objects.create(
                participant=None if identity and n == 0 else participant,
                participant_identity=identity,
                requested_by=user,
            )
            for n, user in enumerate(users)
        ]
        barrier = Barrier(2)

        def approve(claim_id):
            try:
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute("SET lock_timeout = '5s'")
                barrier.wait(timeout=10)
                try:
                    approved = approve_claim_request(claim_id, reviewed_by=owner)
                    return 200, approved.requested_by_id
                except ClaimRequestError as exc:
                    return exc.status_code, None
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(approve, claim.pk) for claim in claims]
            results = [future.result(timeout=20) for future in futures]

        self.assertEqual(sorted(code for code, _ in results), [200, 409])
        winner = next(user_id for code, user_id in results if code == 200)
        for target in participants:
            target.refresh_from_db()
            self.assertEqual(target.user_id, winner)
        states = list(ParticipantClaimRequest.objects.values_list("status", flat=True))
        self.assertCountEqual(states, ["approved", "rejected"])
        if identity:
            identity.refresh_from_db()
            self.assertEqual(identity.user_id, winner)
            self.assertEqual(
                list(GroupMembership.objects.filter(group=group).values_list("user_id", flat=True)), [winner]
            )

    @skipUnlessDBFeature("has_select_for_update")
    def test_identity_and_session_claims_have_one_winner(self):
        self.check_competing_approvals(with_identity=True)

    @skipUnlessDBFeature("has_select_for_update")
    def test_guest_claims_without_identity_have_one_winner(self):
        self.check_competing_approvals(with_identity=False)


class ClaimRejectionTest(TestCase):
    def test_nullable_target_can_be_rejected_only_once_by_another_user(self):
        owner = get_user_model().objects.create_user(username="reject-owner")
        requester = get_user_model().objects.create_user(username="reject-requester")
        group = Group.objects.create(name="却下試験", created_by=owner)
        identity = ParticipantIdentity.objects.create(group=group, display_name="未登録参加者")
        claim = ParticipantClaimRequest.objects.create(participant_identity=identity, requested_by=requester)
        with self.assertRaises(ClaimRequestError) as own_error:
            reject_claim_request(claim.pk, reviewed_by=requester)
        self.assertEqual(own_error.exception.status_code, 403)
        rejected = reject_claim_request(claim.pk, reviewed_by=owner, review_comment="  確認できませんでした  ")
        self.assertEqual(rejected.status, "rejected")
        self.assertEqual(rejected.review_comment, "確認できませんでした")
        self.assertEqual(rejected.reviewed_by_id, owner.pk)
        identity.refresh_from_db()
        self.assertIsNone(identity.user_id)
        with self.assertRaises(ClaimRequestError) as repeated_error:
            reject_claim_request(claim.pk, reviewed_by=owner)
        self.assertEqual(repeated_error.exception.status_code, 409)
