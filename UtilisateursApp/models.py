from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


def validate_gmail(value):
    """Accepte uniquement les adresses qui se terminent par @gmail.com."""
    if not value.lower().endswith("@gmail.com"):
        raise ValidationError(
            "L'adresse e-mail doit se terminer par @gmail.com.",
            code="invalid_gmail",
        )


class User(AbstractUser):
    ROLE_CHOICES = [
        ("USER", "Client particulier"),
        ("COMPANY", "Client entreprise"),
        ("ADMIN", "Administrateur"),
    ]

    email = models.EmailField("adresse e-mail", unique=True, validators=[validate_gmail])
    role = models.CharField("rôle", max_length=10, choices=ROLE_CHOICES, default="USER")

    company_name = models.CharField("nom de l'entreprise", max_length=150, blank=True)
    company_description = models.TextField("description de l'entreprise", blank=True)
    company_skills = models.JSONField("compétences", default=list, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"