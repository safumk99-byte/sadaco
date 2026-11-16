from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("quality", "0001_initial")]

    operations = [
        migrations.AddField(model_name="qualitycheck", name="cutting_ok", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="qualitycheck", name="assembly_ok", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="qualitycheck", name="sticking_ok", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="qualitycheck", name="polishing_ok", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="qualitycheck", name="electrical_ok", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="qualitycheck", name="appearance_ok", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="qualitycheck", name="packing_ok", field=models.BooleanField(default=False)),
    ]
