# Generated by Django 3.2.20 on 2023-09-21 16:16

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("phones", "0027_relaynumber_vendor"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="relaynumber",
            name="deprecated_remaining_minutes",
        ),
    ]
