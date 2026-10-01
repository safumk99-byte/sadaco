from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_userprofile"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="userprofile",
            options={
                "permissions": [
                    ("manage_users", "Can manage SADACO users"),
                    ("manage_roles", "Can manage SADACO roles"),
                    ("manage_permissions", "Can manage SADACO permissions"),
                ]
            },
        ),
    ]
