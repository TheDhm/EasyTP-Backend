import ipaddress
import logging

from django.utils.deprecation import MiddlewareMixin

from .utils.activity_logger import ActivityLogger

logger = logging.getLogger(__name__)


class VisitorLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all page visits for both authenticated and anonymous users
    """

    # Paths to exclude from logging
    EXCLUDE_PATHS = [
        "/admin/",
        "/static/",
        "/media/",
        "/favicon.ico",
        "/robots.txt",
        "/health",
        "/ready",
        "/healthz",
        "/livez",
        "/readyz",
    ]

    # Only log these HTTP methods
    LOG_METHODS = ["GET", "POST"]

    # Kubernetes and internal IP ranges to exclude
    HEALTH_CHECK_IP_RANGES = [
        "10.42.0.0/16",  # Your K8s pod network
        "10.244.0.0/16",  # Common K8s pod network
        "172.16.0.0/12",  # Docker/K8s internal
        "127.0.0.0/8",  # Loopback
    ]

    # Health check user agents
    HEALTH_CHECK_USER_AGENTS = [
        "kube-probe",
        "GoogleHC",
        "health-check",
        "Kubernetes",
        "Go-http-client",
    ]

    def _is_health_check(self, request):
        """
        Detect if this is a health check request
        """
        # Get client IP for checking
        ip = ActivityLogger.get_client_ip(request)

        # Check if IP is in health check ranges
        try:
            client_ip = ipaddress.ip_address(ip)
            for range_str in self.HEALTH_CHECK_IP_RANGES:
                if client_ip in ipaddress.ip_network(range_str, strict=False):
                    return True
        except ValueError, ipaddress.AddressValueError:
            pass

        # Check user agent
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        if any(agent.lower() in user_agent.lower() for agent in self.HEALTH_CHECK_USER_AGENTS):
            return True

        # Check if no referrer + internal IP (common for health checks)
        referrer = request.META.get("HTTP_REFERER", "")
        if not referrer and ip.startswith(("10.", "172.", "192.168.")):
            return True

        return False

    def process_response(self, request, response):
        """
        Log page views for all requests after authentication is complete
        """
        # Skip logging for excluded paths
        if any(request.path.startswith(path) for path in self.EXCLUDE_PATHS):
            return response

        # Only log specific HTTP methods
        if request.method not in self.LOG_METHODS:
            return response

        # Skip health checks
        if self._is_health_check(request):
            return response

        try:
            # Log the page view - at this point, DRF authentication is complete
            ActivityLogger.log_page_view(request)
        except Exception:
            # Don't break the request if logging fails
            logger.exception("Error logging page view")

        return response
