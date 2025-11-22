from django.contrib import admin
from .models import Departament, InventoryUser, Device, SessionLog


@admin.register(Departament)
class DepartamentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(InventoryUser)
class InventoryUserAdmin(admin.ModelAdmin):
    list_display = ("username", "full_name", "departament")
    search_fields = ("username", "full_name")
    list_filter = ("departament",)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        "hostname",
        "device_type",
        "status",
        "departament",
        "assigned_user",
        "ip_address",
        "mac_address",
    )
    list_filter = ("device_type", "status", "departament")
    search_fields = ("hostname", "serial_number", "mac_address", "ip_address")


@admin.register(SessionLog)
class SessionLogAdmin(admin.ModelAdmin):
    list_display = ("device", "user", "login_time", "logout_time", "ip_address")
    list_filter = ("device", "user")
    search_fields = ("device__hostname", "user__username", "ip_address")
