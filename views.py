# inventory/views.py
import csv
import json
from collections import defaultdict
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import DeviceForm, UserPermissionsForm
from .models import Device, Departament, InventoryUser, SessionLog



def user_can_edit_device(user, device):

    if not user.is_authenticated:
        return False


    if hasattr(user, "can_edit_device"):
        return user.can_edit_device(device)


    return user.is_superuser



@login_required
def dashboard(request):
    total_devices = Device.objects.count()


    status_counts_qs = (
        Device.objects.values("status")
        .annotate(c=Count("id"))
        .order_by("status")
    )
    status_display = dict(Device.STATUS_CHOICES)
    status_stats = [
        {"label": status_display[row["status"]], "value": row["c"]}
        for row in status_counts_qs
    ]


    dept_counts = Departament.objects.annotate(device_count=Count("device"))


    recent_devices = (
        Device.objects.select_related("departament", "assigned_user")
        .order_by("-id")[:5]
    )

    # warranty alerts
    today = date.today()
    next_30 = today + timedelta(days=30)

    expired_warranty = Device.objects.filter(
        warranty_expiry__isnull=False,
        warranty_expiry__lt=today,
    )

    expiring_soon = Device.objects.filter(
        warranty_expiry__isnull=False,
        warranty_expiry__gte=today,
        warranty_expiry__lte=next_30,
    )

    context = {
        "total_devices": total_devices,
        "status_stats": status_stats,
        "dept_counts": dept_counts,
        "recent_devices": recent_devices,
        "expired_warranty": expired_warranty,
        "expiring_soon": expiring_soon,
    }
    return render(request, "inventory/dashboard.html", context)



@login_required
def device_list(request):
    q = request.GET.get("q", "")
    status = request.GET.get("status", "")
    dept_id = request.GET.get("dept", "")
    os = request.GET.get("os", "")
    location = request.GET.get("location", "")

    devices = Device.objects.all().select_related("departament", "assigned_user")

    if q:
        devices = devices.filter(hostname__icontains=q)

    if status:
        devices = devices.filter(status=status)

    if dept_id:
        devices = devices.filter(departament_id=dept_id)

    if os:
        devices = devices.filter(os__icontains=os)

    if location:
        devices = devices.filter(location__icontains=location)

    departments = Departament.objects.all()


    user = request.user
    can_add_device = False
    if user.is_authenticated:
        role = getattr(user, "role", None)
        if user.is_superuser or role != InventoryUser.ROLE_VIEWER:
            can_add_device = True

    context = {
        "devices": devices,
        "departments": departments,
        "q": q,
        "status": status,
        "dept_id": dept_id,
        "os": os,
        "location": location,
        "can_add_device": can_add_device,
    }
    return render(request, "inventory/device_list.html", context)


@login_required
def device_detail(request, pk):
    device = get_object_or_404(Device, pk=pk)
    sessions = device.sessions.select_related("user").order_by("-login_time")[:20]
    today = date.today()


    can_edit = user_can_edit_device(request.user, device)

    context = {
        "device": device,
        "sessions": sessions,
        "today": today,
        "can_edit": can_edit,
    }
    return render(request, "inventory/device_detail.html", context)



@login_required
def device_create(request):
    user = request.user


    if (
        hasattr(user, "role")
        and getattr(user, "role", None) == InventoryUser.ROLE_VIEWER
        and not user.is_superuser
    ):
        raise PermissionDenied("You are not allowed to create devices.")

    if request.method == "POST":
        form = DeviceForm(request.POST)
        if form.is_valid():
            device = form.save(commit=False)


            if not user_can_edit_device(user, device):
                raise PermissionDenied(
                    "You can only create devices in locations you have access to."
                )

            device.save()
            return redirect("device_detail", pk=device.pk)
    else:
        form = DeviceForm()

    return render(
        request,
        "inventory/device_form.html",
        {
            "form": form,
            "title": "Add device",
        },
    )


@login_required
def device_edit(request, pk):
    device = get_object_or_404(Device, pk=pk)
    user = request.user


    if not user_can_edit_device(user, device):
        raise PermissionDenied("You are not allowed to edit this device.")

    if request.method == "POST":
        form = DeviceForm(request.POST, instance=device)
        if form.is_valid():
            updated_device = form.save(commit=False)


            if not user_can_edit_device(user, updated_device):
                raise PermissionDenied(
                    "You cannot move this device to a location you don't have access to."
                )

            updated_device.save()
            return redirect("device_detail", pk=device.pk)
    else:
        form = DeviceForm(instance=device)

    return render(
        request,
        "inventory/device_form.html",
        {
            "form": form,
            "title": f"Edit {device.hostname}",
        },
    )


@login_required
def device_export_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="devices.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Hostname",
            "Type",
            "Status",
            "Department",
            "User",
            "IP",
            "MAC",
            "Serial",
            "OS",
            "Location",
            "Purchase date",
            "Warranty expiry",
        ]
    )

    qs = Device.objects.select_related("departament", "assigned_user").all()

    for d in qs:
        writer.writerow(
            [
                d.hostname,
                d.get_device_type_display(),
                d.get_status_display(),
                d.departament.name if d.departament else "",
                d.assigned_user.username if d.assigned_user else "",
                d.ip_address or "",
                d.mac_address or "",
                d.serial_number or "",
                d.os or "",
                d.location or "",
                d.purchase_date or "",
                d.warranty_expiry or "",
            ]
        )

    return response



@login_required
def user_list(request):
    users = InventoryUser.objects.annotate(
        device_count=Count("devices"),
        session_count=Count("sessions"),
    )
    return render(request, "inventory/user_list.html", {"users": users})


@login_required
def user_detail(request, pk):
    user = get_object_or_404(InventoryUser, pk=pk)
    devices = user.devices.select_related("departament").all()
    sessions = user.sessions.select_related("device").order_by("-login_time")[:50]

    total_seconds = sum(
        s.duration_seconds or 0
        for s in sessions
    )

    context = {
        "user_obj": user,
        "devices": devices,
        "sessions": sessions,
        "total_seconds": total_seconds,
    }
    return render(request, "inventory/user_detail.html", context)


@login_required
def edit_user_permissions(request, pk):

    if (
        not request.user.is_superuser
        and getattr(request.user, "role", None) != InventoryUser.ROLE_ADMIN
    ):
        return HttpResponseForbidden("You are not allowed to edit user permissions.")

    user_obj = get_object_or_404(InventoryUser, pk=pk)

    if request.method == "POST":
        form = UserPermissionsForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "User permissions have been updated.")
            return redirect("user_detail", pk=user_obj.pk)
    else:
        form = UserPermissionsForm(instance=user_obj)

    context = {
        "form": form,
        "user_obj": user_obj,
    }
    return render(request, "inventory/user_permissions_form.html", context)



@require_POST
def api_session_log(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    hostname = data.get("hostname")
    username = data.get("username")
    event = data.get("event")          # "login" / "logout"
    timestamp = data.get("timestamp")
    ip_address = data.get("ip_address")

    if not all([hostname, username, event, timestamp]):
        return JsonResponse({"error": "Missing fields"}, status=400)


    try:
        ts = datetime.fromisoformat(timestamp)
        if timezone.is_naive(ts):
            ts = timezone.make_aware(ts, timezone.get_current_timezone())
    except Exception:
        return JsonResponse({"error": "Bad timestamp"}, status=400)

    device = Device.objects.filter(hostname=hostname).first()
    user = InventoryUser.objects.filter(username=username).first()

    if device is None or user is None:
        return JsonResponse({"error": "Device or user not found"}, status=404)

    if event == "login":
        SessionLog.objects.create(
            device=device,
            user=user,
            login_time=ts,
            ip_address=ip_address,
        )
    elif event == "logout":
        session = (
            SessionLog.objects.filter(device=device, user=user, logout_time__isnull=True)
            .order_by("-login_time")
            .first()
        )
        if session:
            session.logout_time = ts
            session.ip_address = ip_address or session.ip_address
            session.save()
    else:
        return JsonResponse({"error": "Unknown event"}, status=400)

    return JsonResponse({"status": "ok"})



@login_required
def live_feed(request):
    sessions = (
        SessionLog.objects.select_related("device", "user")
        .order_by("-login_time")[:20]
    )
    return render(request, "inventory/live_feed.html", {"sessions": sessions})



@login_required
def activity_report(request):
    """
    Raport de activitate pe ultimele 30 de zile.
    Calculăm durata în Python, fără câmpuri extra în DB.
    """
    now = timezone.now()
    cutoff = now - timedelta(days=30)


    sessions = (
        SessionLog.objects
        .filter(login_time__gte=cutoff)
        .select_related("user", "device__departament")
    )


    dept_stats = defaultdict(lambda: {"sessions": 0, "seconds": 0})
    user_stats = defaultdict(lambda: {"sessions": 0, "seconds": 0})
    device_stats = defaultdict(lambda: {"sessions": 0, "seconds": 0})

    for s in sessions:
        if s.logout_time:
            delta = s.logout_time - s.login_time
        else:

            delta = now - s.login_time

        secs = max(0, int(delta.total_seconds()))


        dept_name = (
            s.device.departament.name
            if getattr(s, "device", None) and getattr(s.device, "departament", None)
            else "None"
        )
        dept_stats[dept_name]["sessions"] += 1
        dept_stats[dept_name]["seconds"] += secs


        user_name = s.user.username if s.user else "Unknown"
        user_stats[user_name]["sessions"] += 1
        user_stats[user_name]["seconds"] += secs


        device_name = s.device.hostname if s.device else "Unknown"
        device_stats[device_name]["sessions"] += 1
        device_stats[device_name]["seconds"] += secs

    def build_rows(source, label_key):
        rows = []
        for key, data in source.items():
            hours = round(data["seconds"] / 3600.0, 2) if data["seconds"] else 0
            rows.append(
                {
                    label_key: key,
                    "sessions": data["sessions"],
                    "hours": hours,
                }
            )

        rows.sort(key=lambda r: r["sessions"], reverse=True)
        return rows

    dept_rows = build_rows(dept_stats, "department")
    user_rows = build_rows(user_stats, "user")
    device_rows = build_rows(device_stats, "hostname")


    inactive_devices = (
        Device.objects
        .filter(~Q(sessions__login_time__gte=cutoff))
        .select_related("departament")
        .distinct()
        .order_by("hostname")
    )

    context = {
        "dept_rows": dept_rows,
        "user_rows": user_rows,
        "device_rows": device_rows,
        "top_departments": dept_rows,
        "top_users": user_rows,
        "top_devices": device_rows,
        "inactive_devices": inactive_devices,
    }
    return render(request, "inventory/activity.html", context)



@login_required
def health_report(request):
    today = date.today()
    in_90 = today + timedelta(days=90)


    expired_warranty = (
        Device.objects
        .filter(warranty_expiry__isnull=False, warranty_expiry__lt=today)
        .order_by("warranty_expiry", "hostname")
    )

    expiring_90 = (
        Device.objects
        .filter(
            warranty_expiry__isnull=False,
            warranty_expiry__gte=today,
            warranty_expiry__lte=in_90,
        )
        .order_by("warranty_expiry", "hostname")
    )


    no_user = Device.objects.filter(assigned_user__isnull=True).order_by("hostname")

    no_department = (
        Device.objects.filter(departament__isnull=True).order_by("hostname")
    )

    no_ip = (
        Device.objects
        .filter(Q(ip_address__isnull=True) | Q(ip_address__exact=""))
        .order_by("hostname")
    )

    no_os = (
        Device.objects
        .filter(Q(os__isnull=True) | Q(os__exact=""))
        .order_by("hostname")
    )


    duplicate_macs = (
        Device.objects.exclude(mac_address__isnull=True)
        .exclude(mac_address__exact="")
        .values("mac_address")
        .annotate(c=Count("id"))
        .filter(c__gt=1)
        .order_by("mac_address")
    )


    dup_mac_devices = {}
    if duplicate_macs:
        mac_values = [row["mac_address"] for row in duplicate_macs]
        dup_qs = (
            Device.objects.filter(mac_address__in=mac_values)
            .select_related("departament", "assigned_user")
            .order_by("mac_address", "hostname")
        )
        for d in dup_qs:
            dup_mac_devices.setdefault(d.mac_address, []).append(d)


    cutoff_90 = timezone.now() - timedelta(days=90)

    inactive_90 = (
        Device.objects.filter(
            Q(sessions__isnull=True) | Q(sessions__login_time__lt=cutoff_90)
        )
        .distinct()
        .order_by("hostname")
    )

    never_seen = (
        Device.objects.filter(sessions__isnull=True)
        .distinct()
        .order_by("hostname")
    )

    context = {
        "expired_warranty": expired_warranty,
        "expiring_90": expiring_90,
        "no_user": no_user,
        "no_department": no_department,
        "no_ip": no_ip,
        "no_os": no_os,
        "duplicate_macs": duplicate_macs,
        "dup_mac_devices": dup_mac_devices,
        "inactive_90": inactive_90,
        "never_seen": never_seen,
    }
    return render(request, "inventory/health.html", context)




@login_required
def my_account(request):
    user = request.user

    locations_raw = getattr(user, "allowed_locations", "") or ""
    locations = [p.strip() for p in locations_raw.split(",") if p.strip()]

    role = getattr(user, "role", None)

    if user.is_superuser:
        account_type = "Superuser"
        edit_rights = "You can view and modify everything in the system."
    elif role == InventoryUser.ROLE_ADMIN:
        account_type = "Admin"
        edit_rights = "You can view and modify all devices and manage users."
    elif role == InventoryUser.ROLE_STAFF:
        account_type = "Staff"
        if locations:
            edit_rights = (
                "You can edit devices only in the following locations: "
                + ", ".join(locations)
                + "."
            )
        else:
            edit_rights = "You can edit devices in your assigned locations."
    elif role == InventoryUser.ROLE_VIEWER:
        account_type = "Viewer"
        edit_rights = "You can only view inventory data (no editing)."
    else:
        account_type = "Standard user"
        edit_rights = "You can only view inventory data (no editing)."

    context = {
        "user_obj": user,
        "account_type": account_type,
        "edit_rights": edit_rights,
        "locations": locations,
        "locations_raw": locations_raw,
    }
    return render(request, "inventory/my_account.html", context)



def toggle_theme(request):
    dark = request.session.get("dark_mode", False)
    request.session["dark_mode"] = not dark
    return redirect(request.META.get("HTTP_REFERER", "/"))
