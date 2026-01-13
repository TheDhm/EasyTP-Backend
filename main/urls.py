
# from django.urls import path, include
# from . import views

# app_name = "main"

# urlpatterns = [
#     path('', views.landpage, name="landpage"),
#     path('dashboard/', views.homepage, name="homepage"),
#     path('login/', views.login_request, name="login_request"),
#     path('logout/', views.logout_request, name="logout_request"),
#     path('signup/', views.signup_request, name="signup_request"),

#     path('continue-as-guest/', views.continue_as_guest, name='continue_as_guest'),

#     path('start/<str:app_name>/', views.start_pod, name="start_pod"),
#     # path('start/<str:app_name>/<slug:user_id>/', views.start_pod, name="start_pod"),

#     path('stop/<str:app_name>/', views.stop_pod, name="stop_pod"),
#     # path('stop/<str:app_name>/<slug:user_id>/', views.stop_pod, name="stop_pod"),

#     path('apps/', views.test_apps, name="test_apps"),

#     path('usage_statistics/', views.user_activities, name="user_activities"),

#     # path('check-deployment-status/', views.check_deployment_status, name='check_deployment_status'),

#     # path('group/', views.list_students, name="list_students"),
#     # path('group/<slug:group_id>/', views.list_students, name="list_students"),
#     # path('group/<slug:group_id>/<slug:app_id>/', views.list_students, name="list_students"),

#     path('files/', views.file_explorer, name="file_explorer"),
#     path('files/<path>', views.file_explorer, name="file_explorer"),
#     path('download/<path>', views.download_file, name="download_file"),
# ]
