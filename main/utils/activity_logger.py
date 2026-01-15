import ipaddress

from main.models import UserActivity


class ActivityLogger:
    """Utility class for logging user activities"""

    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request, prioritizing Cloudflare headers"""
        # Priority order for IP headers (Cloudflare → Nginx → Generic → Direct)
        ip_headers = [
            "HTTP_CF_CONNECTING_IP",  # Cloudflare real client IP (highest priority)
            "HTTP_X_REAL_IP",  # Nginx real IP forwarding
            "HTTP_X_FORWARDED_FOR",  # Traditional proxy forwarding
            "REMOTE_ADDR",  # Direct connection (fallback)
        ]

        # DEBUG: Log all available headers for troubleshooting
        debug_info = {}
        for header in ip_headers:
            value = request.META.get(header)
            if value:
                debug_info[header] = value

        # Also check for any other IP-related headers
        for key, value in request.META.items():
            if "IP" in key.upper() or "FORWARD" in key.upper() or "CLIENT" in key.upper():
                if key not in debug_info:
                    debug_info[key] = value

        print(f"DEBUG - Available IP headers: {debug_info}")

        for header in ip_headers:
            ip = request.META.get(header)
            if ip:
                # Handle comma-separated IPs (like X-Forwarded-For)
                if "," in ip:
                    ip = ip.split(",")[0].strip()

                print(f"DEBUG - Checking {header}: {ip}")

                # For Cloudflare header, accept it even if it's IPv6
                if header == "HTTP_CF_CONNECTING_IP":
                    print(f"DEBUG - Using Cloudflare IP: {ip}")
                    return ip

                # For other headers, prefer public IPs but accept private as backup
                if ActivityLogger._is_valid_public_ip(ip):
                    print(f"DEBUG - Using public IP from {header}: {ip}")
                    return ip
                else:
                    print(f"DEBUG - {header} has private/invalid IP: {ip}")

        # Fallback to REMOTE_ADDR even if it's private (for local development)
        fallback_ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
        print(f"DEBUG - Using fallback IP: {fallback_ip}")
        return fallback_ip

    @staticmethod
    def _is_valid_public_ip(ip_str):
        """Check if IP is valid and public (not private/internal)"""
        try:
            ip = ipaddress.ip_address(ip_str.strip())
            # Return True for public IPs (including public IPv6), False for private/internal ones
            # IPv6 addresses from ISPs are typically valid public addresses
            is_public = not (ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast)

            # Special handling for IPv6 - many valid client IPv6 addresses might not pass the public check
            # Accept IPv6 if it's not clearly private/loopback
            if ip.version == 6 and not (ip.is_loopback or ip.is_reserved or ip.is_multicast):
                # Accept IPv6 addresses that aren't link-local (fe80::/10) or unique local (fc00::/7)
                if not (
                    ip.is_link_local
                    or (int(ip) & 0xFE00000000000000000000000000000000)
                    == 0xFC00000000000000000000000000000000
                ):
                    return True

            return is_public
        except (ValueError, ipaddress.AddressValueError):
            return False

    @staticmethod
    def get_user_agent(request):
        """Get user agent from request"""
        return request.META.get("HTTP_USER_AGENT", "")

    @staticmethod
    def log_activity(user, activity_type, request=None, details=None):
        """
        Log user activity

        Args:
            user: User instance
            activity_type: Type of activity (from UserActivity choices)
            request: HTTP request object (optional)
            details: Additional details as dict (optional)
        """
        try:
            # Handle username for different user states
            username = "anonymous"  # Default for anonymous users
            if user and hasattr(user, "username"):
                username = user.username
            elif user is None and details and details.get("username"):
                username = details.get("username")  # Allow override via details

            activity_data = {
                "user": user,
                "username": username,
                "activity_type": activity_type,
                "details": details or {},
            }

            if request:
                activity_data["ip_address"] = ActivityLogger.get_client_ip(request)
                activity_data["user_agent"] = ActivityLogger.get_user_agent(request)

            UserActivity.objects.create(**activity_data)

        except Exception as e:
            # Log the error but don't break the main functionality
            print(f"Error logging activity: {e}")

    @staticmethod
    def log_login(user, request):
        """Log user login"""
        ActivityLogger.log_activity(user=user, activity_type=UserActivity.LOGIN, request=request)

    @staticmethod
    def log_logout(user, request):
        """Log user logout"""
        ActivityLogger.log_activity(user=user, activity_type=UserActivity.LOGOUT, request=request)

    @staticmethod
    def log_pod_start(user, app_name, pod_name, request=None):
        """Log pod start"""
        details = {"app_name": app_name, "pod_name": pod_name}
        ActivityLogger.log_activity(
            user=user, activity_type=UserActivity.POD_START, request=request, details=details
        )

    @staticmethod
    def log_pod_stop(user, app_name, pod_name, request=None):
        """Log pod stop"""
        details = {"app_name": app_name, "pod_name": pod_name}
        ActivityLogger.log_activity(
            user=user, activity_type=UserActivity.POD_STOP, request=request, details=details
        )

    @staticmethod
    def log_file_activity(user, activity_type, filename, file_size=None, request=None):
        """Log file-related activities"""
        details = {
            "filename": filename,
        }
        if file_size:
            details["file_size_mb"] = file_size

        ActivityLogger.log_activity(
            user=user, activity_type=activity_type, request=request, details=details
        )

    @staticmethod
    def log_page_view(request, user=None):
        """Log page view for both authenticated and anonymous users"""
        # Get page details
        page_path = request.path
        http_method = request.method
        referrer = request.META.get("HTTP_REFERER", "")

        details = {
            "page_path": page_path,
            "http_method": http_method,
        }

        if referrer:
            details["referrer"] = referrer

        # If no user provided, try to get from request
        if user is None and hasattr(request, "user") and request.user.is_authenticated:
            user = request.user

        ActivityLogger.log_activity(
            user=user if user and user.is_authenticated else None,
            activity_type=UserActivity.PAGE_VIEW,
            request=request,
            details=details,
        )
