"""Classify server-key mode only; never authenticate, expose, or store a key."""


def stripe_server_key_livemode(value: object) -> bool | None:
    """Return test/live mode, or None for unsupported/obviously invalid forms."""
    if not isinstance(value, str) or any(character.isspace() for character in value):
        return None
    for prefix, livemode in (("sk_test_", False), ("rk_test_", False), ("sk_live_", True), ("rk_live_", True)):
        if value.startswith(prefix) and len(value) > len(prefix):
            return livemode
    return None
