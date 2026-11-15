"""Safely clear legacy business records while preserving identity and PDF masters.

Dry-run is the default. The command simulates the complete dependency-ordered
cleanup inside a transaction and rolls it back. --apply is intended only for
an isolated disposable/staging database after reviewing that dry-run plan.
"""
from collections import Counter

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction
from django.db.models import ForeignKey, OneToOneField
from django.db.models.deletion import Collector, PROTECT, RESTRICT

from accounts.models import UserProfile
from core.models import Department
from products.models import MachineRate, MaterialRateHistory, MaterialVariant, StaffCompensation
from staff.models import Designation, StaffProfile, WorkArea


BUSINESS_APP_LABELS = {
    "accounts", "core", "delivery", "finance", "inventory", "marketing",
    "products", "production", "purchase", "quality", "reports", "sales", "staff",
}

PRESERVED_MODELS = {
    get_user_model(), Group, Permission, ContentType, UserProfile, StaffProfile,
    Department, Designation, WorkArea, MaterialVariant, MaterialRateHistory,
    MachineRate, StaffCompensation,
}


class _DryRunRollback(Exception):
    """Internal sentinel used to roll back a full dry-run simulation."""


def _dependency_order(models):
    """Return child-before-parent order for PROTECT/RESTRICT foreign keys."""
    model_set = set(models)
    outgoing = {model: set() for model in model_set}
    indegree = {model: 0 for model in model_set}

    for child in model_set:
        for field in child._meta.get_fields():
            if not isinstance(field, (ForeignKey, OneToOneField)):
                continue
            if field.remote_field.on_delete not in (PROTECT, RESTRICT):
                continue
            parent = field.remote_field.model
            if parent not in model_set or parent is child:
                continue
            if parent not in outgoing[child]:
                outgoing[child].add(parent)
                indegree[parent] += 1

    ready = sorted(
        (model for model, degree in indegree.items() if degree == 0),
        key=lambda model: model._meta.label_lower,
    )
    ordered = []
    while ready:
        model = ready.pop(0)
        ordered.append(model)
        for parent in sorted(outgoing[model], key=lambda item: item._meta.label_lower):
            indegree[parent] -= 1
            if indegree[parent] == 0:
                ready.append(parent)
                ready.sort(key=lambda item: item._meta.label_lower)

    if len(ordered) != len(model_set):
        cyclic = sorted(
            model._meta.label for model, degree in indegree.items() if degree
        )
        raise CommandError(
            "Cleanup cannot safely order a PROTECT/RESTRICT dependency cycle: "
            + ", ".join(cyclic)
        )
    return ordered


def _delete_model_rows(model, using, counts):
    """Delete one model, handling self-referential PROTECT trees leaf-first."""
    self_protect_fields = [
        field for field in model._meta.fields
        if isinstance(field, (ForeignKey, OneToOneField))
        and field.remote_field.model is model
        and field.remote_field.on_delete in (PROTECT, RESTRICT)
    ]

    def collect_delete(queryset):
        collector = Collector(using=using)
        collector.collect(queryset)
        reached = set(collector.data)
        reached.update(queryset.model for queryset in collector.fast_deletes)
        blocked = reached.intersection(PRESERVED_MODELS)
        if blocked:
            labels = ", ".join(sorted(item._meta.label for item in blocked))
            raise CommandError(
                f"Safety stop while processing {model._meta.label}: "
                f"deletion graph reaches protected models: {labels}"
            )
        for collected_model, objects in collector.data.items():
            counts[collected_model._meta.label] += len(objects)
        for fast_queryset in collector.fast_deletes:
            counts[fast_queryset.model._meta.label] += fast_queryset.count()
        collector.delete()

    if not self_protect_fields:
        collect_delete(model._base_manager.using(using).all())
        return

    while True:
        rows = list(model._base_manager.using(using).only(model._meta.pk.attname))
        if not rows:
            return
        leaf = None
        for row in rows:
            has_children = False
            for field in self_protect_fields:
                children = model._base_manager.using(using).filter(
                    **{field.attname: row.pk}
                ).exclude(pk=row.pk)
                if children.exists():
                    has_children = True
                    break
            if not has_children:
                leaf = row
                break
        if leaf is None:
            raise CommandError(
                f"Cannot safely delete self-referencing PROTECT rows in "
                f"{model._meta.label}: a cycle or self-reference remains."
            )
        collect_delete(model._base_manager.using(using).filter(pk=leaf.pk))


class Command(BaseCommand):
    help = "Dry-run or apply the SADACO PDF baseline cleanup."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Apply the reviewed cleanup plan (default is a rolled-back dry run).",
        )
        parser.add_argument(
            "--database", default=DEFAULT_DB_ALIAS,
            help="Database alias to inspect or clean (default: default).",
        )

    def handle(self, *args, **options):
        using = options["database"]
        User = get_user_model()

        eligible = [
            model for model in apps.get_models()
            if model._meta.app_label in BUSINESS_APP_LABELS
            and model not in PRESERVED_MODELS
            and not model._meta.proxy
            and not model._meta.auto_created
            and model._meta.managed
        ]
        ordered = _dependency_order(eligible)

        protected_models = tuple(sorted(PRESERVED_MODELS, key=lambda m: m._meta.label))
        def protected_snapshot():
            result = {}
            for model in protected_models:
                fields = [field.attname for field in model._meta.concrete_fields]
                rows = model._base_manager.using(using).order_by(
                    model._meta.pk.attname
                ).values_list(*fields)
                result[model._meta.label] = tuple(tuple(row) for row in rows)
            return result

        before = protected_snapshot()
        before_counts = {
            User._meta.label: len(before[User._meta.label]),
            UserProfile._meta.label: len(before[UserProfile._meta.label]),
            StaffProfile._meta.label: len(before.get(StaffProfile._meta.label, ())),
        }
        counts = Counter()

        def simulate_or_apply():
            for model in ordered:
                _delete_model_rows(model, using, counts)

            after = protected_snapshot()
            if before != after:
                raise CommandError(
                    "Protected identity/staff/PDF master records changed; "
                    "transaction rolled back."
                )

        self.stdout.write(self.style.MIGRATE_HEADING("SADACO PDF baseline cleanup plan"))
        self.stdout.write(f"Database alias: {using}")
        self.stdout.write(
            "Protected records before cleanup — "
            f"Users: {before_counts[User._meta.label]}, "
            f"UserProfiles: {before_counts[UserProfile._meta.label]}, "
            f"StaffProfiles: {before_counts[StaffProfile._meta.label]}"
        )

        if options["apply"]:
            try:
                with transaction.atomic(using=using):
                    simulate_or_apply()
            except CommandError:
                raise
            except Exception as exc:
                raise CommandError(
                    f"Cleanup failed safely and the transaction was rolled back: {exc}"
                ) from exc
        else:
            try:
                with transaction.atomic(using=using):
                    simulate_or_apply()
                    raise _DryRunRollback()
            except _DryRunRollback:
                pass
            except CommandError:
                raise
            except Exception as exc:
                raise CommandError(
                    f"Dry-run simulation failed; no changes were committed: {exc}"
                ) from exc

        for label, count in sorted(counts.items()):
            self.stdout.write(f"  {label}: {count} rows")
        total = sum(counts.values())
        self.stdout.write(f"Total rows in deletion plan: {total}")

        if options["apply"]:
            self.stdout.write(self.style.SUCCESS(
                "Cleanup completed. Exact records in all protected models are unchanged."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "DRY RUN ONLY — the full dependency-ordered simulation was rolled back; "
                "no changes were committed."
            ))
