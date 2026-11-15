from django.db import migrations, models
import django.db.models.deletion


def assign_legacy_customer_departments(apps, schema_editor):
    Customer = apps.get_model("sales", "Customer")
    SalesOrder = apps.get_model("sales", "SalesOrder")
    Enquiry = apps.get_model("sales", "Enquiry")
    Quotation = apps.get_model("sales", "Quotation")
    UserProfile = apps.get_model("accounts", "UserProfile")

    for customer in Customer.objects.all().iterator():
        candidates = []
        for department_id in SalesOrder.objects.filter(
            customer_id=customer.pk, responsible_staff__department__isnull=False
        ).values_list("responsible_staff__department_id", flat=True):
            candidates.append(department_id)
        for user_id in Enquiry.objects.filter(customer_id=customer.pk).values_list("created_by_id", flat=True):
            if user_id:
                department_id = UserProfile.objects.filter(user_id=user_id).values_list("department_id", flat=True).first()
                if department_id:
                    candidates.append(department_id)
        for user_id in Quotation.objects.filter(customer_id=customer.pk).values_list("created_by_id", flat=True):
            if user_id:
                department_id = UserProfile.objects.filter(user_id=user_id).values_list("department_id", flat=True).first()
                if department_id:
                    candidates.append(department_id)
        if candidates:
            # Select the most frequently associated department; ties remain deterministic.
            department_id = sorted(set(candidates), key=lambda item: (-candidates.count(item), item))[0]
            customer.department_id = department_id
            customer.save(update_fields=["department"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_department"),
        ("sales", "0006_paymentrecord_accounts_fields"),
        ("accounts", "0005_userprofile_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="department",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="customers", to="core.department",
            ),
        ),
        migrations.RunPython(assign_legacy_customer_departments, migrations.RunPython.noop),
    ]
