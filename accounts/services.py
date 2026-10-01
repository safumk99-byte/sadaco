from django.contrib.auth.models import User
from .models import UserProfile, sync_role_group

def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user, defaults={"role": UserProfile.Role.STAFF}
    )
    sync_role_group(user, profile.role)
    return profile

def update_user(*, user, role, first_name="", last_name="", email="", phone="", is_active=True):
    user.first_name, user.last_name, user.email, user.is_active = first_name, last_name, email, is_active
    user.save(update_fields=["first_name", "last_name", "email", "is_active"])
    profile = get_or_create_profile(user)
    profile.role, profile.phone, profile.is_active = role, phone, is_active
    profile.save(update_fields=["role", "phone", "is_active", "updated_at"])
    sync_role_group(user, role)
    return user

def user_has_role(user, *roles):
    if not user.is_authenticated: return False
    if user.is_superuser: return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.is_active and profile.role in roles)


ROLE_LEVELS = {
    UserProfile.Role.STAFF: 10,
    UserProfile.Role.MANAGER: 20,
    UserProfile.Role.INSTITUTION_ADMIN: 30,
    UserProfile.Role.SUPER_ADMIN: 40,
}


def role_level(role):
    return ROLE_LEVELS.get(role, 0)


def can_assign_role(actor, target_role):
    if actor.is_superuser:
        return True
    actor_profile = getattr(actor, "profile", None)
    if not actor_profile or not actor_profile.is_active:
        return False
    # A role administrator can only create/manage roles below their own level.
    return role_level(target_role) < role_level(actor_profile.role)


def can_manage_target(actor, target):
    if actor.is_superuser:
        return True
    actor_profile = getattr(actor, "profile", None)
    target_profile = getattr(target, "profile", None)
    if not actor_profile or not actor_profile.is_active:
        return False
    if target.is_superuser:
        return False
    if not target_profile:
        return True
    return role_level(target_profile.role) < role_level(actor_profile.role)


def available_roles(actor):
    return [
        (role, label)
        for role, label in UserProfile.Role.choices
        if can_assign_role(actor, role)
    ]
