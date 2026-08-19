from accounts.decorators import role_required

sales_manager_required = role_required("super_admin", "institution_admin", "manager")


from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def customer_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not hasattr(request.user, "customer_profile") or request.user.customer_profile is None:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped
