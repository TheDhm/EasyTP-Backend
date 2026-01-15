import ipaddress

from django.http import Http404
from django.utils.deprecation import MiddlewareMixin

from .utils.activity_logger import ActivityLogger


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
        except (ValueError, ipaddress.AddressValueError):
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
        except Exception as e:
            # Don't break the request if logging fails
            print(f"Error logging page view: {e}")

        return response


class AdminLocalhostMiddleware(MiddlewareMixin):
    """
    Middleware to restrict Django admin access to localhost only
    """

    def process_request(self, request):
        """
        Check if the request is for admin and if it's from localhost
        """
        print(f"Processing request for path: {request.path}")
        # Only apply to admin paths
        if request.path.startswith("/adminpanel/"):
            # Get client IP
            print("Checking client IP for admin access")
            client_ip = self._get_client_ip(request)

            # Check if it's localhost
            if not self._is_localhost(client_ip):
                raise Http404("Admin panel not found")

        return None

    def _get_client_ip(self, request):
        """
        Get the real client IP address, considering proxies
        """
        # Check for forwarded IPs (common with reverse proxies)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # Take the first IP in the chain
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")

        return ip

    def _is_localhost(self, ip):
        """
        Check if the IP is localhost
        """
        if not ip:
            return False

        # Common localhost representations
        localhost_ips = ["127.0.0.1", "::1", "localhost"]

        # Check exact matches
        if ip in localhost_ips:
            return True

        # Check if it's in loopback range
        try:
            import ipaddress

            client_ip = ipaddress.ip_address(ip)
            # IPv4 loopback range
            if client_ip in ipaddress.ip_network("127.0.0.0/8"):
                return True
            # IPv6 loopback
            if client_ip in ipaddress.ip_network("::1/128"):
                return True
        except (ValueError, ipaddress.AddressValueError):
            pass

        return False
