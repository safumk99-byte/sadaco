from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profile = getattr(request.user, "profile", None)
            if profile is None or not profile.is_active or profile.role not in roles:
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
