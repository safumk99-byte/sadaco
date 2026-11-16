from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0011_salesordersequence"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="salesorder",
            name="advance_exception_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="advance_exception_approved_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_sales_advance_exceptions", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="advance_exception_approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="credit_exception_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="credit_exception_approved_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_sales_credit_exceptions", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="credit_exception_approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
