from decimal import Decimal
from django.db import migrations


def seed_staff_compensation(apps, schema_editor):
    StaffProfile = apps.get_model("staff", "StaffProfile")
    Compensation = apps.get_model("products", "StaffCompensation")

    monthly = {
        "manager": Decimal("25000"),
        "muhaimin": Decimal("15000"),
        "junaid": Decimal("11000"),
        "ashiq": Decimal("10000"),
    }
    per_work = {"shibili", "sakeer"}

    for staff in StaffProfile.objects.select_related("user").all():
        user = staff.user
        name = (f"{user.first_name} {user.last_name}".strip() or user.username).casefold()
        username = user.username.casefold()
        salary = next((amount for key, amount in monthly.items() if key in name or key in username), None)
        payment_type = "monthly" if salary is not None else ("per_work" if any(key in name or key in username for key in per_work) else None)
        if payment_type:
            Compensation.objects.update_or_create(
                staff_id=staff.pk,
                defaults={"payment_type": payment_type, "monthly_salary": salary, "is_active": True},
            )


class Migration(migrations.Migration):
    dependencies = [("products", "0010_material_master_and_costing_rates")]
    operations = [migrations.RunPython(seed_staff_compensation, migrations.RunPython.noop)]
