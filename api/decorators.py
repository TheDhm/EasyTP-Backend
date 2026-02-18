from functools import wraps

from rest_framework import status
from rest_framework.response import Response

from main.utils.turnstile import verify_turnstile


def require_turnstile(view_func):
    """Decorator that validates a Cloudflare Turnstile token before allowing the view to proceed."""

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        token = request.data.get("turnstile_token")
        if not token:
            return Response(
                {"detail": "Turnstile token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client_ip = request.META.get("HTTP_CF_CONNECTING_IP", request.META.get("REMOTE_ADDR"))

        if not verify_turnstile(token, remote_ip=client_ip):
            return Response(
                {"detail": "Bot verification failed."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return view_func(self, request, *args, **kwargs)

    return wrapper
