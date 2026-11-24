from django.db import migrations, models


def entreprises_vers_clients(apps, schema_editor):
    """Le rôle « client entreprise » n'existe plus : ces comptes deviennent de simples clients."""
    User = apps.get_model("UtilisateursApp", "User")
    User.objects.filter(role="COMPANY").update(role="USER")


class Migration(migrations.Migration):

    dependencies = [
        ("UtilisateursApp", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(entreprises_vers_clients, migrations.RunPython.noop),
        migrations.RemoveField(model_name="user", name="company_name"),
        migrations.RemoveField(model_name="user", name="company_description"),
        migrations.RemoveField(model_name="user", name="company_skills"),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[("USER", "Client"), ("ADMIN", "Administrateur")],
                default="USER", max_length=10, verbose_name="rôle",
            ),
        ),
    ]
