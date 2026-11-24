from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import DeleteView, TemplateView, UpdateView

from Projet_App.mixins import ProjetCourantMixin

from .forms import EstimationForm
from .models import Estimation


class EstimationMixin(ProjetCourantMixin):
    model = Estimation
    onglet = "estimation"

    def get_object(self, queryset=None):
        # Un projet a une seule estimation : pas besoin d'un <pk> dans l'URL.
        return get_object_or_404(Estimation, projet=self.projet)

    def get_success_url(self):
        return reverse("estimation_detail", args=[self.projet.pk])


class EstimationDetailView(EstimationMixin, TemplateView):
    """Affiche l'estimation, ou un message si elle n'a pas encore été générée."""

    template_name = "estimation/estimation_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estimation"] = Estimation.objects.filter(projet=self.projet).first()
        return context


class EstimationUpdateView(EstimationMixin, UpdateView):
    form_class = EstimationForm
    template_name = "estimation/estimation_form.html"
    context_object_name = "estimation"

    def form_valid(self, form):
        messages.success(self.request, "Estimation modifiée.")
        return super().form_valid(form)


class EstimationDeleteView(EstimationMixin, DeleteView):
    template_name = "estimation/estimation_confirm_delete.html"
    context_object_name = "estimation"

    def form_valid(self, form):
        messages.success(self.request, "Estimation supprimée.")
        return super().form_valid(form)
