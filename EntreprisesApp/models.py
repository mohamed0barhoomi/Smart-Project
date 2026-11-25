from django.db import models


class Entreprise(models.Model):
    """Une entreprise de la base, gérée par l'administrateur (CRUD).
    Elle servira plus tard à recommander des entreprises aux utilisateurs."""

    TYPES_OPPORTUNITE = [
        ("STAGE", "Stage"),
        ("EMPLOI", "Emploi"),
        ("ALTERNANCE", "Alternance"),
        ("FREELANCE", "Freelance"),
    ]

    nom = models.CharField("nom", max_length=150, unique=True)
    secteur = models.CharField("secteur", max_length=100)
    competences = models.TextField(
        "compétences",
        help_text="Compétences séparées par des virgules. Exemple : Python, Django, SQL",
    )
    localisation = models.CharField("localisation", max_length=100)
    type_opportunite = models.CharField("type d'opportunité", max_length=20, choices=TYPES_OPPORTUNITE)
    description = models.TextField("description", blank=True)
    site_web = models.URLField("site web", blank=True)
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "entreprise"
        verbose_name_plural = "entreprises"

    def liste_competences(self):
        return [c.strip() for c in self.competences.split(",") if c.strip()]

    def __str__(self):
        return self.nom