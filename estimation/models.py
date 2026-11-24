"""Mêmes modèles que SmartProjects (Projet_App.Projet et Estimation_App.Estimation),
pour que les deux projets restent compatibles."""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinLengthValidator, MinValueValidator
from django.db import models


class Projet(models.Model):
    """Même champs que Projet_App.Projet dans SmartProjects."""

    nom = models.CharField(
        max_length=120,
        validators=[MinLengthValidator(3, "Le nom doit contenir au moins 3 caractères.")],
    )
    description = models.TextField(blank=True)
    proprietaire = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projets"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["proprietaire", "nom"], name="nom_projet_unique_par_user"),
        ]

    def __str__(self):
        return self.nom


class Estimation(models.Model):
    """Coût, délai et résumé d'un projet (même modèle que Estimation_App.Estimation).

    Dans SmartProjects, l'estimation est créée par l'IA (bouton « Générer » du chat).
    Ici, l'administrateur peut la consulter, la modifier ou la supprimer."""

    # OneToOneField : un projet a au plus UNE estimation (projet.estimation)
    projet = models.OneToOneField(Projet, on_delete=models.CASCADE, related_name="estimation")
    resume = models.TextField("Résumé du projet", blank=True)
    # DecimalField plutôt que FloatField : pas d'erreurs d'arrondi sur les montants
    cout = models.DecimalField(
        "Coût estimé (DT)", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"), "Le coût ne peut pas être négatif.")],
    )
    delai = models.DecimalField(
        "Délai estimé (mois)", max_digits=5, decimal_places=1,
        validators=[MinValueValidator(Decimal("0"), "Le délai ne peut pas être négatif.")],
    )
    hypotheses = models.TextField(
        "Hypothèses", blank=True,
        help_text="Ce sur quoi repose l'estimation (taille de l'équipe, fonctionnalités prises en compte...).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Estimation — {self.projet.nom}"
