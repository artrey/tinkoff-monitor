# Generated by Django 4.0.3 on 2022-03-06 21:05

import django.db.models.deletion
from django.db import migrations, models

import apps.tgbot.drf_json_encoder


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("monitor", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotifySettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("need_rub", models.BooleanField(default=False)),
                ("need_usd", models.BooleanField(default=False)),
                ("need_eur", models.BooleanField(default=False)),
                (
                    "atm",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="notify_settings", to="monitor.atm"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TelegramUser",
            fields=[
                ("id", models.CharField(max_length=32, primary_key=True, serialize=False)),
                (
                    "extra_data",
                    models.JSONField(blank=True, encoder=apps.tgbot.drf_json_encoder.JSONEncoder, null=True),
                ),
                ("has_subscription", models.BooleanField(default=False)),
                (
                    "atms",
                    models.ManyToManyField(
                        related_name="subscribers", through="tgbot.NotifySettings", to="monitor.atm"
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="notifysettings",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="notify_settings", to="tgbot.telegramuser"
            ),
        ),
    ]
