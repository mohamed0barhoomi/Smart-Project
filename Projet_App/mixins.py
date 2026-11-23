"""
Mixin partagé par le chat, les besoins et les diagrammes.

Ces trois parties ont des URLs de la forme  projets/<projet_pk>/...
Ce mixin :
  1. récupère le projet à partir de l'URL (et vérifie qu'il appartient à l'utilisateur),
  2. le met dans self.projet et dans le template ({{ projet }}),
  3. limite la liste d'objets à ceux de ce projet.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404

from .models import Projet


class ProjetCourantMixin(LoginRequiredMixin):
    onglet = ""   # nom de l'onglet actif dans le menu du projet (chat, besoins, diagrammes)

    def dispatch(self, request, *args, **kwargs):
        # dispatch() est la toute première méthode appelée par une vue basée sur une classe.
        # get_object_or_404 renvoie une page 404 si le projet n'existe pas
        # ou n'appartient pas à l'utilisateur connecté.
        if request.user.is_authenticated:
            self.projet = get_object_or_404(Projet, pk=kwargs["projet_pk"], proprietaire=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # self.model est Besoin ou Diagramme selon la vue
        return self.model.objects.filter(projet=self.projet)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["projet"] = self.projet
        context["onglet"] = self.onglet
        return context
