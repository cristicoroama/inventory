from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import redirect

from .models import InventoryUser


def _get_profile(django_user):

    if not getattr(django_user, "is_authenticated", False):
        return None
    try:
        return InventoryUser.objects.get(username=django_user.username)
    except InventoryUser.DoesNotExist:
        return None


def can_edit_device(django_user, device) -> bool:

    if getattr(django_user, "is_superuser", False):
        return True

    profile = _get_profile(django_user)
    if profile is None:

        return False
    return profile.can_edit_device(device)


def require_role(*allowed_roles):

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect("login")

            #adm ; bypass la tot
            if getattr(user, "is_superuser", False):
                return view_func(request, *args, **kwargs)

            profile = _get_profile(user)
            user_role = profile.role if profile else None

            if user_role not in allowed_roles:
                return HttpResponseForbidden("You do not have rights for this action.")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator



require_admin = require_role("admin")
require_staff_or_admin = require_role("admin", "staff")
