from django.db import migrations, models
import sales.models


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0007_customer_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="customer_no",
            field=models.CharField(default=sales.models.generate_customer_no, editable=False, max_length=24, unique=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="customer_type",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name="enquiry",
            name="channel",
            field=models.CharField(choices=[("phone", "Phone"), ("direct_visit", "Direct Visit"), ("whatsapp", "WhatsApp"), ("instagram", "Instagram"), ("facebook", "Facebook"), ("walk_in", "Walk-in"), ("referral", "Referral"), ("other", "Other")], max_length=20),
        ),
    ]
