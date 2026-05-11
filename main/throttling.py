from rest_framework.throttling import (
    AnonRateThrottle,
    ScopedRateThrottle,
    UserRateThrottle,
)


def _cf_ip(request):
    cf = request.META.get("HTTP_CF_CONNECTING_IP")
    return cf.strip() if cf else None


class CloudflareAnonRateThrottle(AnonRateThrottle):
    def get_ident(self, request):
        return _cf_ip(request) or super().get_ident(request)


class CloudflareUserRateThrottle(UserRateThrottle):
    def get_ident(self, request):
        return _cf_ip(request) or super().get_ident(request)


class CloudflareScopedRateThrottle(ScopedRateThrottle):
    def get_ident(self, request):
        return _cf_ip(request) or super().get_ident(request)
