from django.contrib import messages
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import InscriptionForm


class InscriptionView(CreateView):
    form_class = InscriptionForm
    template_name = "compte/inscription.html"
    success_url = reverse_lazy("projet_list")

    def form_valid(self, form):
        # form_valid est appelée quand le formulaire est correct.
        # super() enregistre l'utilisateur, puis on le connecte directement.
        reponse = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Bienvenue sur SmartProjects !")
        return reponse
