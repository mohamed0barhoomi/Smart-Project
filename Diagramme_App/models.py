from django.core.validators import MinLengthValidator
from django.db import models

from Projet_App.models import Projet

# Serveur public PlantUML qui transforme le code texte en image SVG.
PLANTUML_SERVEUR = "https://www.plantuml.com/plantuml/svg/"


class Diagramme(models.Model):
    """Un diagramme UML stocké sous forme de code PlantUML.

    PlantUML est un langage texte pour décrire des diagrammes UML, par exemple :
        @startuml
        actor Client
        Client --> (Passer commande)
        @enduml
    Le texte est facile à stocker en base, à modifier dans un formulaire,
    et un serveur PlantUML le transforme en image.
    """

    TYPE_CHOICES = [
        ("usecase", "Diagramme de cas d'utilisation"),
        ("classe", "Diagramme de classes"),
    ]
    SOURCE_CHOICES = [
        ("ia", "Généré par l'IA"),
        ("manuel", "Ajouté manuellement"),
    ]

    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name="diagrammes")
    type_diagramme = models.CharField("Type", max_length=10, choices=TYPE_CHOICES)
    titre = models.CharField(
        max_length=150,
        validators=[MinLengthValidator(3, "Le titre doit contenir au moins 3 caractères.")],
    )
    code_plantuml = models.TextField("Code PlantUML")
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="manuel")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["type_diagramme", "-updated_at"]

    def __str__(self):
        return self.titre

    @property
    def image_url(self):
        """URL de l'image du diagramme.

        Le serveur PlantUML accepte le code encodé en hexadécimal précédé de « ~h ».
        .encode("utf-8").hex() transforme le texte en suite de caractères 0-9a-f,
        ce qui peut être placé sans problème dans une URL.
        """
        return PLANTUML_SERVEUR + "~h" + self.code_plantuml.encode("utf-8").hex()
