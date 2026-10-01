from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse


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


def api_role_required(*roles):
    """Role check for React/API endpoints; never redirects an API request to HTML login."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({"detail": "Authentication required."}, status=401)
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            profile = getattr(request.user, "profile", None)
            if profile is None or not profile.is_active or profile.role not in roles:
                return JsonResponse({"detail": "You do not have permission to access this resource."}, status=403)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
