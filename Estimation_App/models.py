from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from Projet_App.models import Projet


class Estimation(models.Model):
    """Coût, délai et résumé d'un projet.

    L'estimation est toujours créée par l'IA (bouton « Générer » du chat).
    L'utilisateur peut ensuite la modifier ou la supprimer ;
    une nouvelle génération remplace l'estimation existante."""

    # OneToOneField : un projet a au plus UNE estimation.
    # related_name="estimation" permet d'écrire : projet.estimation
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
