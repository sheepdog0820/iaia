"""A lost mutation response is not proof that Google rejected the write."""

import requests


class GoogleWriteUncertain(Exception):
    """No credentials, provider response, or target may escape in this exception."""


def google_write_request(send, *args, **kwargs):
    try:
        response = send(*args, **kwargs)
    except requests.RequestException:
        # Even a connection error may follow a transmitted request or applied write.
        raise GoogleWriteUncertain from None
    if response.status_code == 408 or response.status_code >= 500:
        raise GoogleWriteUncertain
    return response
