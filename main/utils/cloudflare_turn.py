import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Cloudflare Realtime TURN credential-generation endpoint. Returns an iceServers
# array with short-lived username/credential for turn.cloudflare.com.
_CF_TURN_URL = (
    "https://rtc.live.cloudflare.com/v1/turn/keys/{key_id}/credentials/generate-ice-servers"
)


def generate_turn_credentials(ttl=86400):
    """Mint short-lived Cloudflare TURN credentials.

    Returns a ``(username, credential)`` tuple, or ``None`` when TURN is not
    configured or the API call fails — callers should degrade gracefully
    (deploy without TURN env) rather than break the deploy.
    """
    key_id = settings.CLOUDFLARE_TURN_KEY_ID
    api_token = settings.CLOUDFLARE_TURN_API_TOKEN
    if not key_id or not api_token:
        logger.warning("Cloudflare TURN not configured; deploying webrtc app without a TURN relay")
        return None

    try:
        resp = requests.post(
            _CF_TURN_URL.format(key_id=key_id),
            headers={"Authorization": f"Bearer {api_token}"},
            json={"ttl": ttl},
            timeout=5,
        )
        resp.raise_for_status()
        ice_servers = resp.json()["iceServers"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        logger.error("Failed to generate Cloudflare TURN credentials: %s", exc)
        return None

    # generate-ice-servers returns a list (STUN entry + credentialed TURN entry);
    # the older single-object shape is tolerated too.
    if isinstance(ice_servers, dict):
        ice_servers = [ice_servers]

    # The credentialed entry is the TURN one (it carries username/credential);
    # the bare STUN entry has neither.
    for entry in ice_servers:
        username = entry.get("username")
        credential = entry.get("credential")
        if username and credential:
            return username, credential

    logger.error("Cloudflare TURN response had no credentialed iceServers entry")
    return None
