import base64
import binascii
import hashlib
import os
import uuid
from datetime import timedelta

from django.core.exceptions import SuspiciousOperation
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from main.forms import ActivityFilterForm
from main.models import AccessGroup, App, DefaultUser, Instances, Pod, UserActivity
from main.utils.activity_logger import ActivityLogger

# Import from shared modules
from shared.files import (
    get_actual_storage_usage,
    get_sub_files_secure,
    safe_base64_decode,
    sanitize_filename,
    save_file_secure,
    validate_and_sanitize_path,
)
from shared.kubernetes import (
    create_ingress,
    create_service,
    delete_ingress,
    deploy_app,
    display_apps,
    load_k8s_config,
    stop_deployed_pod,
)

from .permissions import CanAccessApp, IsAdminUser
from .serializers import (
    FileUploadSerializer,
    LoginSerializer,
    SignupSerializer,
    UserActivitySerializer,
    UserSerializer,
)


class LandingPageView(APIView):
    """API endpoint for landing page"""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "authenticated": request.user.is_authenticated,
                "message": "Welcome to EasyTP Cloud Platform",
                "user": UserSerializer(request.user).data
                if request.user.is_authenticated
                else None,
            }
        )


class SignupView(APIView):
    """User registration endpoint"""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Log account creation
            ActivityLogger.log_activity(
                user=user, activity_type=UserActivity.ACCOUNT_CREATED, request=request
            )

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """User login endpoint with consistent response format"""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            # Log login activity
            ActivityLogger.log_login(user, request)

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """Logout endpoint"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user

            # Check if user is a guest before logout operations
            is_guest_user = user.is_guest()

            # Log logout activity (before potential user deletion)
            ActivityLogger.log_logout(user, request)

            # Blacklist the refresh token if provided
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            # Delete guest user after logout operations
            if is_guest_user:
                user.delete()
                return Response({"message": "Guest session ended"}, status=status.HTTP_200_OK)

            return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContinueAsGuestView(APIView):
    """Continue as guest endpoint"""

    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Get or create guest group
            guest_group, created = AccessGroup.objects.get_or_create(name=AccessGroup.GUEST)

            # Create temporary guest user
            guest_username = f"guest_{uuid.uuid4().hex[:8]}"
            guest_user = DefaultUser.objects.create_user(
                username=guest_username,
                email=f"{guest_username}@guest.local",
                password=uuid.uuid4().hex,
                role=DefaultUser.GUEST,
                group=guest_group,
                first_name="Guest",
                last_name="User",
            )

            # Log guest access
            ActivityLogger.log_login(guest_user, request)

            # Generate JWT tokens
            refresh = RefreshToken.for_user(guest_user)
            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(guest_user).data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DashboardView(APIView):
    """User dashboard endpoint"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Determine template type based on role
        if user.is_superuser or user.role == DefaultUser.ADMIN:
            template_type = "admin"
        elif user.role == DefaultUser.TEACHER:
            template_type = "teacher_home"
        elif user.role == DefaultUser.STUDENT or user.role == DefaultUser.GUEST:
            template_type = "student_home"
        else:
            template_type = "student_home"

        # Calculate dashboard statistics using available model data
        running_apps = Pod.objects.filter(pod_user=user, is_deployed=True).count()

        # Convert storage from MB to bytes for frontend consistency
        storage_used = user.size_uploaded * 1024 * 1024  # Convert MB to bytes

        # Calculate total files from user directory
        total_files = 0
        try:
            if user.role in [DefaultUser.TEACHER, DefaultUser.ADMIN] or user.is_superuser:
                user_path = "/READONLY/"
            else:
                user_path = f"/USERDATA/{user.username}/"

            # Count files using the existing secure function
            files, directories = get_sub_files_secure(user_path, "")
            total_files = len(files)

            # Count files in subdirectories recursively
            import os

            if os.path.exists(user_path):
                for root, dirs, files_in_dir in os.walk(user_path):
                    # Skip hidden files and directories
                    files_in_dir = [f for f in files_in_dir if not f.startswith(".")]
                    total_files += len(files_in_dir)
                # Subtract the root level files to avoid double counting
                total_files -= len(files)
        except Exception:
            total_files = 0

        return Response(
            {
                "user": UserSerializer(user).data,
                "template_type": template_type,
                "role": user.role,
                "apps_available": user.apps_available(),
                "running_apps": running_apps,
                "total_files": total_files,
                "storage_used": storage_used,
            }
        )


class AppsView(APIView):
    """Apps listing with deployment status"""

    permission_classes = [IsAuthenticated]

    @method_decorator(never_cache)
    def get(self, request):
        user = request.user

        # Get available apps based on user role
        if user.role == DefaultUser.TEACHER or user.role == DefaultUser.ADMIN:
            apps = App.objects.all()
        else:
            if user.group:
                apps = user.group.apps.all()
            else:
                apps = App.objects.none()

        # Use existing display_apps function to get status data
        try:
            apps_data = display_apps(apps, user)
            return Response({"apps": apps_data, "user_role": user.role, "authenticated": True})
        except Exception as e:
            return Response(
                {"error": str(e), "apps": {}, "user_role": user.role, "authenticated": True},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class StartPodView(APIView):
    """Start pod endpoint"""

    permission_classes = [IsAuthenticated, CanAccessApp]

    def post(self, request, app_name):
        user = request.user
        user_id = request.data.get("user_id")

        # Handle user_id for admin/teacher roles
        if user_id and user.role not in [DefaultUser.STUDENT, DefaultUser.GUEST]:
            try:
                target_user = DefaultUser.objects.get(id=user_id)
            except DefaultUser.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            target_user = user

        # Get app and pod - let Http404 propagate naturally
        app = get_object_or_404(App, name=app_name)
        pod = get_object_or_404(Pod, pod_user=target_user, app_name=app_name)

        try:
            cleaned_username = target_user.username.replace("_", "-").replace(".", "-").lower()
            readonly_volume = target_user.role in [DefaultUser.STUDENT, DefaultUser.GUEST]

            # Deploy the app
            deploy_app(
                username=target_user.username,
                pod_name=pod.pod_name,
                app_name=app_name.lower(),
                image=app.image,
                vnc_password=hashlib.md5(pod.pod_vnc_password.encode("utf-8")).hexdigest(),
                user_hostname=cleaned_username,
                readonly=readonly_volume,
            )

            pod.is_deployed = True
            pod.save()

            # Create service and ingress
            create_service(pod_name=pod.pod_name, app_name=app_name.lower())
            novnc_url = create_ingress(
                pod_name=pod.pod_name, app_name=app_name.lower(), user_hostname=cleaned_username
            )

            # Update instance
            instance, created = Instances.objects.get_or_create(pod=pod, instance_name=pod.pod_name)
            if novnc_url:
                instance.novnc_url = f"https://{novnc_url}"
                instance.save()

            # Log activity
            ActivityLogger.log_pod_start(target_user, app_name, pod.pod_name, request)

            # Schedule pod stop
            stop_deployed_pod(pod_id=pod.id, pod_name=pod.pod_name, app_name=app_name)

            return Response(
                {
                    "status": "starting",
                    "message": "Pod deployment initiated",
                    "pod_name": pod.pod_name,
                    "novnc_url": instance.novnc_url if hasattr(instance, "novnc_url") else None,
                    "deployment_status": True,  # Optimistic status for immediate UI update
                    "is_deployed": True,
                }
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StopPodView(APIView):
    """Stop pod endpoint"""

    permission_classes = [IsAuthenticated, CanAccessApp]

    def post(self, request, app_name):
        user = request.user
        user_id = request.data.get("user_id")

        # Handle user_id for admin/teacher roles
        if user_id and user.role not in [DefaultUser.STUDENT, DefaultUser.GUEST]:
            try:
                target_user = DefaultUser.objects.get(id=user_id)
            except DefaultUser.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            target_user = user

        # Get pod - let Http404 propagate naturally
        pod = get_object_or_404(Pod, pod_user=target_user, app_name=app_name)

        try:
            # Import Kubernetes clients
            from kubernetes import client
            from kubernetes.client.rest import ApiException

            # Load Kubernetes config
            load_k8s_config()

            api_instance = client.CoreV1Api()
            apps_instance = client.AppsV1Api()

            pod_name = pod.pod_name
            app_name_lower = app_name.lower()

            # Delete Kubernetes resources
            try:
                # Delete deployment
                apps_instance.delete_namespaced_deployment(
                    name=f"{app_name_lower}-deployment-{pod_name}", namespace="apps"
                )

                # Delete service
                api_instance.delete_namespaced_service(
                    name=f"{app_name_lower}-service-{pod_name}", namespace="apps"
                )

                # Delete ingress
                delete_ingress(pod_name, app_name_lower)

            except ApiException:
                # Log but don't fail if resources don't exist
                pass

            # Update pod status
            pod.is_deployed = False
            pod.save()

            # Delete instance record
            try:
                instance = Instances.objects.get(pod=pod, instance_name=pod_name)
                instance.delete()
            except Instances.DoesNotExist:
                pass  # Instance already deleted

            # Log activity
            ActivityLogger.log_pod_stop(target_user, app_name, pod_name, request)

            return Response(
                {"status": "stopped", "message": "Pod stopped successfully", "pod_name": pod_name}
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileExplorerView(APIView):
    """File explorer endpoint"""

    permission_classes = [IsAuthenticated]

    def _get_user_path(self, user):
        """Get user's base path and readonly status based on role."""
        if user.role in [DefaultUser.TEACHER, DefaultUser.ADMIN] or user.is_superuser:
            return "/READONLY/", False
        return f"/USERDATA/{user.username}/", False

    @method_decorator(never_cache)
    def get(self, request, path=None):
        """Secure file browsing endpoint"""
        user = request.user
        user_path, is_readonly = self._get_user_path(user)

        # Ensure user directory exists
        try:
            os.makedirs(user_path, exist_ok=True)
        except OSError:
            return Response(
                {"error": "Unable to access user directory"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            # Decode and validate path
            if path:
                decoded_path = safe_base64_decode(path)
                validated_path = validate_and_sanitize_path(decoded_path, user_path)
            else:
                validated_path = ""

            # Set up navigation
            current_path = f"/{validated_path}" if validated_path else "/"

            # Calculate parent path for navigation
            if validated_path:
                parent_parts = validated_path.split("/")[:-1]
                parent_path = "/".join(parent_parts) if parent_parts else ""
                parent_path_encoded = (
                    base64.urlsafe_b64encode(parent_path.encode("utf-8")).decode()
                    if parent_path
                    else ""
                )
            else:
                parent_path_encoded = ""

        except SuspiciousOperation:
            return Response(
                {"error": "Invalid path access attempt"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get directory contents
        try:
            files, directories = get_sub_files_secure(user_path, validated_path)
        except (OSError, IOError):
            return Response(
                {"error": "Unable to access directory"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Calculate storage usage and permissions
        storage_usage = None
        permissions = {
            "can_upload": not is_readonly,
            "can_delete": not is_readonly,
            "can_download": True,
        }

        if user.role in [DefaultUser.STUDENT, DefaultUser.GUEST]:
            # Calculate storage usage for students/guests
            actual_usage = get_actual_storage_usage(user_path)
            # Update user's stored usage to match reality
            user.size_uploaded = actual_usage
            user.save()
            storage_usage = {
                "current_mb": actual_usage,
                "limit_mb": float(user.upload_limit),
                "percentage": min(100, (actual_usage / user.upload_limit) * 100)
                if user.upload_limit > 0
                else 0,
            }

        response_data = {
            "current_path": current_path,
            "parent_path_encoded": parent_path_encoded,
            "files": files,
            "directories": directories,
            "is_readonly": is_readonly,
            "storage_usage": storage_usage,
            "permissions": permissions,
        }

        return Response(response_data)

    def post(self, request, path=None):
        """File upload endpoint"""
        user = request.user
        user_path, is_readonly = self._get_user_path(user)

        # Check if uploads are allowed for this user/path
        if is_readonly:
            return Response(
                {"error": "Upload not allowed in read-only directory"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate uploaded file
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data["file"]
        file_size_bytes = uploaded_file.size
        file_size_mb = file_size_bytes / (1024 * 1024)

        try:
            # Decode and validate path
            if path:
                decoded_path = safe_base64_decode(path)
                validated_path = validate_and_sanitize_path(decoded_path, user_path)
            else:
                validated_path = ""

        except SuspiciousOperation:
            return Response(
                {"error": "Invalid path access attempt"}, status=status.HTTP_400_BAD_REQUEST
            )

        # User storage limit check for students/guests
        if user.role in [DefaultUser.STUDENT, DefaultUser.GUEST]:
            current_usage = get_actual_storage_usage(user_path)
            if file_size_mb + current_usage > user.upload_limit:
                available = user.upload_limit - current_usage
                return Response(
                    {"error": f"Upload would exceed storage limit. Available: {available:.2f}MB"},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

        # Sanitize filename (using shared module)
        clean_filename = sanitize_filename(uploaded_file.name)

        try:
            # Construct safe save path
            save_dir = os.path.join(user_path, validated_path) if validated_path else user_path
            save_path = os.path.join(save_dir, clean_filename)

            # Ensure directory exists
            os.makedirs(save_dir, exist_ok=True)

            # Ensure we're not overwriting existing files
            counter = 1
            original_name, ext = os.path.splitext(clean_filename)
            while os.path.exists(save_path):
                clean_filename = f"{original_name}_{counter}{ext}"
                save_path = os.path.join(save_dir, clean_filename)
                counter += 1

            # Save file securely
            save_file_secure(save_path, uploaded_file)

            # Update user's uploaded size for students/guests
            if user.role in [DefaultUser.STUDENT, DefaultUser.GUEST]:
                current_usage = get_actual_storage_usage(user_path)
                user.size_uploaded = current_usage + file_size_mb
                user.save()

            # Log activity
            ActivityLogger.log_file_activity(
                user=user,
                activity_type=UserActivity.FILE_UPLOAD,
                filename=clean_filename,
                file_size=file_size_mb,
                request=request,
            )

            return Response(
                {
                    "message": f'File "{clean_filename}" uploaded successfully',
                    "filename": clean_filename,
                    "size_mb": round(file_size_mb, 2),
                },
                status=status.HTTP_201_CREATED,
            )

        except (IOError, OSError):
            return Response(
                {"error": "Error saving file"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, path):
        """File deletion endpoint"""
        user = request.user
        user_path, is_readonly = self._get_user_path(user)

        # Check if deletes are allowed for this user/path
        if is_readonly:
            return Response(
                {"error": "Delete not allowed in read-only directory"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            # Decode and validate path
            decoded_path = safe_base64_decode(path)
            validated_path = validate_and_sanitize_path(decoded_path, user_path)

            if not validated_path:
                return Response({"error": "Invalid file path"}, status=status.HTTP_400_BAD_REQUEST)

            full_file_path = os.path.join(user_path, validated_path)

            # Security checks
            if not os.path.exists(full_file_path):
                return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)

            if not os.path.isfile(full_file_path) or os.path.islink(full_file_path):
                return Response(
                    {"error": "Can only delete regular files"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Get file size before deletion
            try:
                file_size_bytes = os.path.getsize(full_file_path)
                file_size_mb = file_size_bytes / (1024 * 1024)
            except OSError:
                file_size_mb = 0

            # Get filename for response
            filename = os.path.basename(validated_path)

            # Delete the file
            os.remove(full_file_path)

            # Update user's uploaded size for students/guests
            if user.role in [DefaultUser.STUDENT, DefaultUser.GUEST]:
                current_usage = get_actual_storage_usage(user_path)
                user.size_uploaded = current_usage
                user.save()

            # Log activity
            ActivityLogger.log_file_activity(
                user=user,
                activity_type=UserActivity.FILE_DELETE,
                filename=filename,
                file_size=file_size_mb,
                request=request,
            )

            return Response(
                {
                    "message": f'File "{filename}" deleted successfully',
                    "filename": filename,
                    "size_mb_freed": round(file_size_mb, 2),
                },
                status=status.HTTP_200_OK,
            )

        except (SuspiciousOperation, UnicodeDecodeError, binascii.Error):
            return Response({"error": "Invalid path encoding"}, status=status.HTTP_400_BAD_REQUEST)
        except (IOError, OSError):
            return Response(
                {"error": "Error deleting file"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DownloadFileView(APIView):
    """File download endpoint"""

    permission_classes = [IsAuthenticated]

    def _get_user_path(self, user):
        """Get user's base path based on role."""
        if user.role in [DefaultUser.TEACHER, DefaultUser.ADMIN] or user.is_superuser:
            return "/READONLY/"
        return f"/USERDATA/{user.username}/"

    @method_decorator(never_cache)
    def get(self, request, path):
        """Secure file download endpoint"""
        user = request.user

        try:
            # Decode and validate path
            decoded_path = safe_base64_decode(path)
            user_path = self._get_user_path(user)

            # Validate path
            validated_path = validate_and_sanitize_path(decoded_path, user_path)

            if not validated_path:
                raise Http404("Invalid file path")

            full_path = os.path.join(user_path, validated_path)

            # Security checks
            if (
                not os.path.exists(full_path)
                or not os.path.isfile(full_path)
                or os.path.islink(full_path)
            ):
                raise Http404("File not found")

            # Get clean filename for download (using shared module)
            filename = sanitize_filename(os.path.basename(validated_path))

            # Use FileResponse for secure download
            try:
                response = FileResponse(
                    open(full_path, "rb"), as_attachment=True, filename=filename
                )

                # Log download activity
                ActivityLogger.log_file_activity(
                    user=user,
                    activity_type=UserActivity.FILE_DOWNLOAD,
                    filename=filename,
                    request=request,
                )

                return response

            except IOError:
                raise Http404("Cannot access file")

        except (SuspiciousOperation, UnicodeDecodeError, binascii.Error):
            raise Http404("Invalid request")


class UserActivitiesView(APIView):
    """User activities dashboard for admins"""

    permission_classes = [IsAuthenticated, IsAdminUser]

    @method_decorator(never_cache)
    def get(self, request):
        # Get filter parameters
        filter_form = ActivityFilterForm(request.GET)
        activities = UserActivity.objects.select_related("user").all()

        # Apply filters
        if filter_form.is_valid():
            if filter_form.cleaned_data.get("user"):
                activities = activities.filter(user=filter_form.cleaned_data["user"])

            if filter_form.cleaned_data.get("activity_type"):
                activities = activities.filter(
                    activity_type=filter_form.cleaned_data["activity_type"]
                )

            if filter_form.cleaned_data.get("start_date"):
                activities = activities.filter(
                    timestamp__gte=filter_form.cleaned_data["start_date"]
                )

            if filter_form.cleaned_data.get("end_date"):
                activities = activities.filter(timestamp__lte=filter_form.cleaned_data["end_date"])

        # Search functionality
        search_query = request.GET.get("search", "")
        if search_query:
            activities = activities.filter(
                Q(user__username__icontains=search_query)
                | Q(user__email__icontains=search_query)
                | Q(ip_address__icontains=search_query)
            )

        # Pagination
        page_size = int(request.GET.get("page_size", 50))
        paginator = Paginator(activities, page_size)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # Activity statistics
        stats = {
            "total_activities": activities.count(),
            "today_activities": activities.filter(timestamp__date=timezone.now().date()).count(),
            "week_activities": activities.filter(
                timestamp__gte=timezone.now() - timedelta(days=7)
            ).count(),
            "unique_users": activities.values("user").distinct().count(),
        }

        return Response(
            {
                "stats": stats,
                "activities": UserActivitySerializer(page_obj.object_list, many=True).data,
                "pagination": {
                    "count": paginator.count,
                    "num_pages": paginator.num_pages,
                    "current_page": page_obj.number,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                    "next_page_number": page_obj.next_page_number()
                    if page_obj.has_next()
                    else None,
                    "previous_page_number": page_obj.previous_page_number()
                    if page_obj.has_previous()
                    else None,
                },
                "filters": {"search_query": search_query, "form_data": request.GET.dict()},
            }
        )


class UpdateAppImageView(APIView):
    """CI webhook to update app image tag after build."""

    permission_classes = [AllowAny]

    def post(self, request):
        # Verify webhook secret
        secret = request.headers.get("X-Webhook-Secret")
        if secret != os.environ.get("WEBHOOK_SECRET"):
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        app_name = request.data.get("app_name")
        image_tag = request.data.get("image_tag")

        if not app_name or not image_tag:
            return Response(
                {"error": "Missing app_name or image_tag"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            app = App.objects.get(name=app_name)
            app.image = f"{app_name}:{image_tag}"
            app.save()
            return Response({"status": "updated", "image": app.image})
        except App.DoesNotExist:
            return Response({"error": "App not found"}, status=status.HTTP_404_NOT_FOUND)
