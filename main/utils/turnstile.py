import requests
from django.conf import settings


def verify_turnstile(token, remote_ip=None):
    """Verify a Cloudflare Turnstile token. Returns True if valid."""
    payload = {
        "secret": settings.TURNSTILE_SECRET_KEY,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    resp = requests.post(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=payload,
        timeout=5,
    )
    return resp.json().get("success", False)
