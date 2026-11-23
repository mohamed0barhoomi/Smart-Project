from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.urls import reverse


class Projet(models.Model):
    """Un projet logiciel décrit par l'utilisateur."""

    nom = models.CharField(
        max_length=120,
        validators=[MinLengthValidator(3, "Le nom doit contenir au moins 3 caractères.")],
    )
    description = models.TextField(
        blank=True,
        help_text="Résumé court. La description détaillée se fait dans le chat.",
    )
    # settings.AUTH_USER_MODEL = le modèle utilisateur du projet (User par défaut).
    # related_name="projets" permet d'écrire : request.user.projets.all()
    proprietaire = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projets"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]          # les plus récents en premier
        constraints = [
            # Un utilisateur ne peut pas avoir deux projets avec le même nom
            models.UniqueConstraint(fields=["proprietaire", "nom"], name="nom_projet_unique_par_user"),
        ]

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse("projet_detail", args=[self.pk])
