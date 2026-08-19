from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .services import can_manage_staff


def staff_manager_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not can_manage_staff(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped
