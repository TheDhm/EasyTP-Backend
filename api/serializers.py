import re

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from main.models import AccessGroup, App, DefaultUser, Instances, Pod, UserActivity


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile data"""

    apps_available = serializers.CharField(read_only=True)

    class Meta:
        model = DefaultUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "group",
            "upload_limit",
            "size_uploaded",
            "apps_available",
            "date_joined",
            "is_active",
        ]
        read_only_fields = ["id", "username", "date_joined", "apps_available"]


class AccessGroupSerializer(serializers.ModelSerializer):
    """Serializer for access groups"""

    class Meta:
        model = AccessGroup
        fields = ["id", "name"]


class AppSerializer(serializers.ModelSerializer):
    """Serializer for applications"""

    groups = AccessGroupSerializer(source="group", many=True, read_only=True)

    class Meta:
        model = App
        fields = ["id", "name", "image", "app_type", "groups"]


class PodSerializer(serializers.ModelSerializer):
    """Serializer for pods"""

    pod_user_username = serializers.CharField(source="pod_user.username", read_only=True)

    class Meta:
        model = Pod
        fields = [
            "id",
            "pod_user",
            "pod_user_username",
            "app_name",
            "pod_name",
            "pod_vnc_user",
            "pod_vnc_password",
            "date_created",
            "date_modified",
            "pod_namespace",
            "is_deployed",
        ]
        read_only_fields = ["id", "date_created", "date_modified", "pod_user_username"]


class InstanceSerializer(serializers.ModelSerializer):
    """Serializer for instances"""

    pod_details = PodSerializer(source="pod", read_only=True)

    class Meta:
        model = Instances
        fields = [
            "id",
            "pod",
            "pod_details",
            "instance_name",
            "date_created",
            "date_modified",
            "novnc_url",
        ]
        read_only_fields = ["id", "date_created", "date_modified"]


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for user activities"""

    user_username = serializers.CharField(source="user.username", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    activity_display = serializers.CharField(source="get_activity_type_display", read_only=True)

    class Meta:
        model = UserActivity
        fields = [
            "id",
            "user",
            "user_username",
            "user_email",
            "username",
            "activity_type",
            "activity_display",
            "timestamp",
            "ip_address",
            "country",
            "user_agent",
            "details",
        ]
        read_only_fields = ["id", "timestamp", "user_username", "user_email", "activity_display"]


class SignupSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = DefaultUser
        fields = [
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def validate_username(self, value):
        """Validate username to prevent reserved names and ensure uniqueness"""
        # List of reserved usernames
        reserved_usernames = [
            "admin",
            "api",
            "www",
            "easytp",
            "easytpcloud",
            "root",
            "system",
            "administrator",
            "user",
            "guest",
            "student",
            "teacher",
            "support",
            "help",
            "info",
            "mail",
            "email",
            "test",
            "demo",
            "default",
            "null",
            "undefined",
            "none",
            "login",
            "logout",
            "signup",
            "register",
            "dashboard",
            "home",
            "index",
            "main",
            "app",
            "apps",
            "config",
            "settings",
            "profile",
            "account",
            "accounts",
            "service",
            "services",
            "auth",
            "authentication",
            "authorization",
            "security",
            "backup",
            "database",
            "db",
            "server",
            "client",
            "public",
            "private",
            "static",
            "media",
            "assets",
            "resources",
            "files",
            "uploads",
            "downloads",
        ]

        # Check if username is reserved (case-insensitive)
        if value.lower() in [name.lower() for name in reserved_usernames]:
            raise serializers.ValidationError(f"Username '{value}' is reserved and cannot be used.")

        # Usernames become DNS labels (lab hostnames) and directory names: ASCII only.
        if not re.fullmatch(r"[a-z0-9]([a-z0-9_-]*[a-z0-9])?", value, re.IGNORECASE):
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, hyphens, and underscores, "
                "and must start and end with a letter or number."
            )

        # Check minimum length
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")

        # Check maximum length
        if len(value) > 30:
            raise serializers.ValidationError("Username must be no more than 30 characters long.")

        # Uniqueness on the lab hostname form ("_" and "." map to "-"), so a new "a-b"
        # cannot share an ingress host with an existing "a_b".
        pattern = "^" + re.sub(r"[-_]", "[-_.]", value) + "$"
        if DefaultUser.objects.filter(username__iregex=pattern).exists():
            raise serializers.ValidationError("A user with this username already exists.")

        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm", None)
        password = validated_data.pop("password")

        # Self-signup is always a student in the Guest group; roles are granted by admins.
        validated_data["group"], _ = AccessGroup.objects.get_or_create(name=AccessGroup.GUEST)
        user = DefaultUser.objects.create_user(
            password=password, role=DefaultUser.STUDENT, **validated_data
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError("Invalid credentials")
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled")
            attrs["user"] = user
        else:
            raise serializers.ValidationError("Must include username and password")

        return attrs


class AppStatusSerializer(serializers.Serializer):
    """Serializer for app status data"""

    deployment_status = serializers.BooleanField()
    is_deployed = serializers.BooleanField()
    novnc_url = serializers.URLField(allow_null=True)
    vnc_pass = serializers.CharField()


class AppsDataSerializer(serializers.Serializer):
    """Serializer for apps display data"""

    def to_representation(self, instance):
        # This will be a dictionary where keys are app names and values are status data
        return instance


class FileItemSerializer(serializers.Serializer):
    """Serializer for individual file/directory items"""

    name = serializers.CharField()
    path = serializers.CharField()
    is_dir = serializers.BooleanField()
    size = serializers.IntegerField(allow_null=True)
    escaped_name = serializers.CharField()


class StorageUsageSerializer(serializers.Serializer):
    """Serializer for storage usage information"""

    current_mb = serializers.FloatField()
    limit_mb = serializers.FloatField()
    percentage = serializers.FloatField()


class FilePermissionsSerializer(serializers.Serializer):
    """Serializer for file operation permissions"""

    can_upload = serializers.BooleanField()
    can_delete = serializers.BooleanField()
    can_download = serializers.BooleanField()


class FileExplorerSerializer(serializers.Serializer):
    """Serializer for file explorer response"""

    current_path = serializers.CharField()
    parent_path_encoded = serializers.CharField(allow_blank=True)
    files = FileItemSerializer(many=True)
    directories = FileItemSerializer(many=True)
    is_readonly = serializers.BooleanField()
    storage_usage = StorageUsageSerializer(allow_null=True)
    permissions = FilePermissionsSerializer()


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload validation"""

    file = serializers.FileField()

    def validate_file(self, value):
        # File size validation (10MB limit)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size must not exceed 10MB.")

        # Additional file type validation can be added here if needed
        return value
