# Generated by Django 5.2.4 on 2025-07-18 10:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pracownicy', '0006_alter_pracownik_rola'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pracownik',
            name='zespol',
            field=models.CharField(blank=True, choices=[('hr', 'HR'), ('it', 'IT Support'), ('dev', 'Development'), ('marketing', 'Marketing'), ('sales', 'Sprzedaż'), ('finance', 'Finanse'), ('management', 'Zarządzanie'), ('mixed', 'Mixed Team'), ('bus_it', 'Bus IT Systems')], max_length=50, null=True),
        ),
    ]
