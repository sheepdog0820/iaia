"""Keep malformed signed JWTs inside the library's documented error contract."""

from unittest import TestCase

import jwt


class JWTDependencySecurityTests(TestCase):
    # Public, isolated fixture; never an application signing key.
    signing_key = "jwt-security-regression-fixture-32-bytes"

    def test_valid_token_still_round_trips(self):
        payload = {"sub": "fixture-user", "aud": "tableno-test"}
        token = jwt.encode(payload, self.signing_key, algorithm="HS256")

        self.assertEqual(
            jwt.decode(token, self.signing_key, algorithms=["HS256"], audience="tableno-test"),
            payload,
        )

    def test_deeply_nested_signed_payload_raises_jwt_error(self):
        payload = b'{"nested":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}"
        token = jwt.api_jws.encode(payload, self.signing_key, algorithm="HS256")

        with self.assertRaises(jwt.DecodeError):
            jwt.decode(token, self.signing_key, algorithms=["HS256"])

    def test_invalid_time_claim_types_raise_jwt_errors(self):
        for claim in ("exp", "nbf", "iat"):
            for value in (None, [], {}):
                with self.subTest(claim=claim, value=value):
                    token = jwt.encode({claim: value}, self.signing_key, algorithm="HS256")

                    with self.assertRaises(jwt.PyJWTError):
                        jwt.decode(token, self.signing_key, algorithms=["HS256"])

    def test_wrong_signature_is_rejected(self):
        token = jwt.encode({"sub": "fixture-user"}, "other-fixture-signing-key-32-bytes", algorithm="HS256")

        with self.assertRaises(jwt.InvalidSignatureError):
            jwt.decode(token, self.signing_key, algorithms=["HS256"])
