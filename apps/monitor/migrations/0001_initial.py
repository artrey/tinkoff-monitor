# Generated by Django 4.0.3 on 2022-03-05 22:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ATM",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("address", models.TextField()),
                ("worktime", models.CharField(max_length=256)),
                ("lon", models.DecimalField(decimal_places=15, max_digits=18)),
                ("lat", models.DecimalField(decimal_places=15, max_digits=18)),
            ],
        ),
        migrations.CreateModel(
            name="ATMLastInfo",
            fields=[
                ("rub", models.IntegerField(default=0)),
                ("usd", models.IntegerField(default=0)),
                ("eur", models.IntegerField(default=0)),
                (
                    "atm",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="last_info",
                        serialize=False,
                        to="monitor.atm",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("out_per_transaction", models.TextField(blank=True, null=True)),
                ("out_banknotes", models.TextField(blank=True, null=True)),
                ("in_banknotes", models.TextField(blank=True, null=True)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ATMHistoryInfo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rub", models.IntegerField(default=0)),
                ("usd", models.IntegerField(default=0)),
                ("eur", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "atm",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="history", to="monitor.atm"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]