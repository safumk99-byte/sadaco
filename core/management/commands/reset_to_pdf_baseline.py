"""Safely clear legacy business records while preserving identity and PDF masters.

This command is intentionally dry-run by default. Use --apply only against an
isolated disposable/staging database after reviewing the printed deletion plan.
It never deletes auth users, groups, permissions, user profiles or staff profiles.
"""
from collections import Counter

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction
from django.db.models.deletion import Collector

from accounts.models import UserProfile
from core.models import Department
from products.models import MachineRate, MaterialRateHistory, MaterialVariant, StaffCompensation
from staff.models import Designation, StaffProfile, WorkArea


# Business apps whose legacy operational records are eligible for replacement.
BUSINESS_APP_LABELS = {
    "accounts", "core", "delivery", "finance", "inventory", "marketing",
    "products", "production", "purchase", "quality", "reports", "sales", "staff",
}

# These are identity, staff-master, or PDF-authoritative configuration records.
PRESERVED_MODELS = {
    get_user_model(),
    Group,
    Permission,
    ContentType,
    UserProfile,
    StaffProfile,
    Department,
    Designation,
    WorkArea,
    MaterialVariant,
    MaterialRateHistory,
    MachineRate,
    StaffCompensation,
}


class Command(BaseCommand):
    help = (
        "Dry-run or apply the SADACO PDF baseline cleanup. "
        "All existing user accounts and staff profiles are preserved."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Actually delete eligible legacy business records (default is dry-run).",
        )
        parser.add_argument(
            "--database", default=DEFAULT_DB_ALIAS,
            help="Database alias to inspect or clean (default: default).",
        )

    def handle(self, *args, **options):
        using = options["database"]
        alias = using
        User = get_user_model()

        before = {
            "users": User.objects.using(alias).count(),
            "user_profiles": UserProfile.objects.using(alias).count(),
            "staff_profiles": StaffProfile.objects.using(alias).count(),
        }

        eligible = []
        for model in apps.get_models():
            if model._meta.app_label not in BUSINESS_APP_LABELS:
                continue
            if model in PRESERVED_MODELS or model._meta.proxy or model._meta.auto_created:
                continue
            if model._meta.managed:
                eligible.append(model)

        collector = Collector(using=using)
        try:
            for model in eligible:
                collector.collect(model._base_manager.using(using).all())
        except Exception as exc:
            raise CommandError(
                f"Cleanup plan could not be collected safely; no data was deleted: {exc}"
            ) from exc

        collected_models = set(collector.data)
        for queryset in collector.fast_deletes:
            collected_models.add(queryset.model)

        protected = collected_models.intersection(PRESERVED_MODELS)
        if protected:
            names = ", ".join(sorted(m._meta.label for m in protected))
            raise CommandError(
                "Safety stop: the deletion graph reaches protected identity/staff/PDF "
                f"master models: {names}. No data was deleted."
            )

        counts = Counter()
        for model, objects in collector.data.items():
            counts[model._meta.label] += len(objects)
        for queryset in collector.fast_deletes:
            counts[queryset.model._meta.label] += queryset.count()

        self.stdout.write(self.style.MIGRATE_HEADING("SADACO PDF baseline cleanup plan"))
        self.stdout.write(f"Database alias: {using}")
        self.stdout.write(
            "Protected before cleanup — "
            f"Users: {before['users']}, UserProfiles: {before['user_profiles']}, "
            f"StaffProfiles: {before['staff_profiles']}"
        )
        if counts:
            for label, count in sorted(counts.items()):
                self.stdout.write(f"  {label}: {count} rows")
        else:
            self.stdout.write("  No eligible legacy business rows found.")

        total = sum(counts.values())
        self.stdout.write(f"Total rows in deletion graph: {total}")

        if not options["apply"]:
            self.stdout.write(self.style.WARNING(
                "DRY RUN ONLY — nothing was deleted. Re-run with --apply only on "
                "the reviewed isolated staging/disposable database."
            ))
            return

        with transaction.atomic(using=using):
            # Re-collect inside the transaction to avoid applying a stale plan.
            fresh = Collector(using=using)
            for model in eligible:
                fresh.collect(model._base_manager.using(using).all())
            fresh_models = set(fresh.data)
            for queryset in fresh.fast_deletes:
                fresh_models.add(queryset.model)
            newly_protected = fresh_models.intersection(PRESERVED_MODELS)
            if newly_protected:
                raise CommandError(
                    "Safety stop: protected models entered the refreshed deletion graph."
                )
            fresh.delete()

            after = {
                "users": User.objects.using(alias).count(),
                "user_profiles": UserProfile.objects.using(alias).count(),
                "staff_profiles": StaffProfile.objects.using(alias).count(),
            }
            if before != after:
                raise CommandError(
                    "Identity/staff row counts changed during cleanup; transaction rolled back. "
                    f"Before={before}; after={after}"
                )

        self.stdout.write(self.style.SUCCESS(
            "Cleanup completed. All User, UserProfile and StaffProfile row counts are unchanged. "
            "PDF master data/configuration was excluded from deletion."
        ))
