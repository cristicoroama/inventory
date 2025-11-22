from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("devices/", views.device_list, name="device_list"),
    path("devices/<int:pk>/", views.device_detail, name="device_detail"),
    path("devices/add/", views.device_create, name="device_create"),
    path("devices/<int:pk>/edit/", views.device_edit, name="device_edit"),
    path("devices/export/", views.device_export_csv, name="device_export_csv"),

    path("users/", views.user_list, name="user_list"),
    path("users/<int:pk>/", views.user_detail, name="user_detail"),

    path("activity/", views.activity_report, name="activity"),
    path("health/", views.health_report, name="health"),
    path("live-feed/", views.live_feed, name="live_feed"),

    path("api/session-log/", views.api_session_log, name="api_session_log"),
    path("toggle-theme/", views.toggle_theme, name="toggle_theme"),
    path("account/", views.my_account, name="my_account"),
    path("", views.dashboard, name="dashboard"),
    path("devices/", views.device_list, name="device_list"),
    path("users/<int:pk>/", views.user_detail, name="user_detail"),
    path("users/<int:pk>/permissions/", views.edit_user_permissions, name="edit_user_permissions"),


]
