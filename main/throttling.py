from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


def _client_ip(request):
    cf = request.META.get("HTTP_CF_CONNECTING_IP")
    if cf:
        return cf.strip()
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class CloudflareAnonRateThrottle(AnonRateThrottle):
    def get_ident(self, request):
        return _client_ip(request) or super().get_ident(request)


class CloudflareUserRateThrottle(UserRateThrottle):
    def get_ident(self, request):
        return _client_ip(request) or super().get_ident(request)
