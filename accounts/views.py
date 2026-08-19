from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth.models import User
from .decorators import role_required
from .forms import LoginForm, UserCreateForm, UserEditForm, AdminPasswordChangeForm
from .models import Notification, UserProfile
from .services import can_assign_role, can_manage_target, get_or_create_profile, update_user, available_roles

class Login(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # Customers use the same login page, but must never land in the
        # internal management dashboard.
        if hasattr(self.request.user, "customer_profile"):
            return reverse("sales:portal_dashboard")
        return super().get_success_url()

@login_required
def logout_view(request):
    logout(request)
    return redirect("accounts:login")

def can_manage(user):
    if user.is_superuser: return True
    return get_or_create_profile(user).role in (UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN)

@role_required(UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN)
def user_create(request):
    form = UserCreateForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        if not can_assign_role(request.user, form.cleaned_data["role"]):
            form.add_error("role", "You cannot assign this role.")
        else:
            form.save()
            messages.success(request, "User created successfully.")
            return redirect("accounts:user_list")
    return render(request, "accounts/user_form.html", {"title":"Create User","form":form})

@login_required
def user_list(request):
    if not can_manage(request.user):
        raise PermissionDenied
    users = User.objects.select_related("profile").order_by("username")
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()
    if query:
        from django.db.models import Q
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )
    if role:
        users = users.filter(profile__role=role)
    if status == "active":
        users = users.filter(is_active=True, profile__is_active=True)
    elif status == "inactive":
        users = users.filter(Q(is_active=False) | Q(profile__is_active=False))

    all_users = User.objects.select_related("profile")
    active_count = all_users.filter(is_active=True, profile__is_active=True).count()
    role_counts = {
        value: all_users.filter(profile__role=value).count()
        for value, _ in UserProfile.Role.choices
    }
    return render(request, "accounts/user_list.html", {
        "title": "Users & Roles",
        "users": users,
        "active_count": active_count,
        "role_counts": role_counts,
        "query": query,
        "role": role,
        "status": status,
        "role_choices": UserProfile.Role.choices,
    })

@role_required(UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN)
def user_edit(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if not can_manage_target(request.user, target):
        raise PermissionDenied
    profile = get_or_create_profile(target)
    initial = {
        "first_name": target.first_name,
        "last_name": target.last_name,
        "email": target.email,
        "phone": profile.phone,
        "role": profile.role,
        "is_active": target.is_active and profile.is_active,
    }
    form = UserEditForm(
        request.POST or None,
        initial=initial,
        actor=request.user,
        current_role=profile.role,
    )
    if request.method == "POST" and form.is_valid():
        if not can_assign_role(request.user, form.cleaned_data["role"]):
            form.add_error("role", "You cannot assign this role.")
        elif target == request.user and not form.cleaned_data["is_active"]:
            form.add_error("is_active", "You cannot deactivate your own account.")
        else:
            update_user(
                user=target,
                role=form.cleaned_data["role"],
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                email=form.cleaned_data["email"],
                phone=form.cleaned_data["phone"],
                is_active=form.cleaned_data["is_active"],
            )
            messages.success(request, "User updated successfully.")
            return redirect("accounts:user_list")
    return render(
        request,
        "accounts/user_form.html",
        {"title": f"Edit User: {target.username}", "form": form, "editing": True, "target": target},
    )

@role_required(UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN)
def user_password(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if not can_manage_target(request.user, target):
        raise PermissionDenied
    form = AdminPasswordChangeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        target.set_password(form.cleaned_data["new_password"])
        target.save(update_fields=["password"])
        messages.success(request, "Password updated successfully.")
        return redirect("accounts:user_list")
    return render(
        request,
        "accounts/password_form.html",
        {"title": f"Change Password: {target.username}", "form": form, "target": target},
    )

@login_required
def my_profile(request):
    return render(request, "accounts/my_profile.html", {"title":"My Profile","profile":get_or_create_profile(request.user)})


@login_required
def notifications(request):
    items = request.user.notifications.all()[:30]
    return render(request, "accounts/notifications.html", {
        "title": "Notifications",
        "notifications": items,
    })


@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return redirect(notification.url or "accounts:notifications")


@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect(request.META.get("HTTP_REFERER") or "core:dashboard")
