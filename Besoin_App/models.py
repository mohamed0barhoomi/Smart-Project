from django.core.validators import MinLengthValidator
from django.db import models

from Projet_App.models import Projet


class Besoin(models.Model):
    TYPE_CHOICES = [
        ("F", "Fonctionnel"),
        ("NF", "Non fonctionnel"),
    ]
    PRIORITE_CHOICES = [
        ("haute", "Haute"),
        ("moyenne", "Moyenne"),
        ("basse", "Basse"),
    ]
    # Catégories classiques des besoins non fonctionnels
    CATEGORIE_CHOICES = [
        ("", "—"),
        ("performance", "Performance"),
        ("securite", "Sécurité"),
        ("ergonomie", "Ergonomie"),
        ("disponibilite", "Disponibilité"),
        ("maintenabilite", "Maintenabilité"),
        ("portabilite", "Portabilité"),
        ("autre", "Autre"),
    ]
    SOURCE_CHOICES = [
        ("ia", "Généré par l'IA"),
        ("manuel", "Ajouté manuellement"),
    ]

    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name="besoins")
    type_besoin = models.CharField("Type", max_length=2, choices=TYPE_CHOICES, default="F")
    titre = models.CharField(
        max_length=150,
        validators=[MinLengthValidator(5, "Le titre doit contenir au moins 5 caractères.")],
    )
    description = models.TextField(blank=True)
    priorite = models.CharField("Priorité", max_length=10, choices=PRIORITE_CHOICES, default="moyenne")
    categorie = models.CharField(
        "Catégorie", max_length=20, choices=CATEGORIE_CHOICES, blank=True,
        help_text="Uniquement pour les besoins non fonctionnels.",
    )
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="manuel")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["type_besoin", "pk"]

    def __str__(self):
        return self.titre

    @property
    def code(self):
        """Identifiant lisible affiché dans l'interface : BF-01, BNF-03...
        @property permet de l'utiliser comme un attribut : {{ besoin.code }}"""
        prefixe = "BF" if self.type_besoin == "F" else "BNF"
        rang = Besoin.objects.filter(
            projet_id=self.projet_id, type_besoin=self.type_besoin, pk__lt=self.pk
        ).count() + 1
        return f"{prefixe}-{rang:02d}"
