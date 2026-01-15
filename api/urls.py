from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from . import views

app_name = "api"

urlpatterns = [
    # Authentication endpoints
    path(
        "auth/",
        include(
            [
                path("login/", views.LoginView.as_view(), name="login"),
                path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
                path("verify/", TokenVerifyView.as_view(), name="token_verify"),
                path("logout/", views.LogoutView.as_view(), name="logout"),
                path("signup/", views.SignupView.as_view(), name="signup"),
                path(
                    "continue-as-guest/",
                    views.ContinueAsGuestView.as_view(),
                    name="continue_as_guest",
                ),
            ]
        ),
    ),
    # Main endpoints - matching existing URL structure
    path("", views.LandingPageView.as_view(), name="landing"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("apps/", views.AppsView.as_view(), name="apps"),
    # Pod management
    path("start/<str:app_name>/", views.StartPodView.as_view(), name="start_pod"),
    path("stop/<str:app_name>/", views.StopPodView.as_view(), name="stop_pod"),
    # File management
    path("files/", views.FileExplorerView.as_view(), name="file_explorer_root"),
    path("files/<path:path>/", views.FileExplorerView.as_view(), name="file_explorer"),
    path("download/<path:path>/", views.DownloadFileView.as_view(), name="download_file"),
    # User activities (admin only)
    path("usage_statistics/", views.UserActivitiesView.as_view(), name="user_activities"),
]
