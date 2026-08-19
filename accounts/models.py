from django.contrib.auth.models import Group, User
from django.db import models

class UserProfile(models.Model):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        INSTITUTION_ADMIN = "institution_admin", "Institution Admin"
        MANAGER = "manager", "Manager"
        STAFF = "staff", "Staff"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=40, choices=Role.choices, default=Role.STAFF)
    is_active = models.BooleanField(default=True)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("manage_users", "Can manage SADACO users"),
            ("manage_roles", "Can manage SADACO roles"),
            ("manage_permissions", "Can manage SADACO permissions"),
        ]

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

def role_group_name(role):
    return f"SADACO:{role}"

def sync_role_group(user, role):
    group, _ = Group.objects.get_or_create(name=role_group_name(role))
    user.groups.set([group])
    return group

def get_user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return UserProfile.Role.SUPER_ADMIN
    profile = getattr(user, "profile", None)
    return profile.role if profile and profile.is_active else None


class Notification(models.Model):
    class Type(models.TextChoices):
        INFO = "info", "Information"
        ORDER = "order", "Order"
        ENQUIRY = "enquiry", "Enquiry"
        STOCK = "stock", "Stock Alert"
        TASK = "task", "Task"
        PAYMENT = "payment", "Payment"
        SYSTEM = "system", "System"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(
        max_length=20, choices=Type.choices, default=Type.INFO
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.NORMAL
    )
    title = models.CharField(max_length=180)
    message = models.TextField(blank=True)
    url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.title}"
