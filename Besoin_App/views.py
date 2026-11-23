from django.contrib import messages
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from Projet_App.mixins import ProjetCourantMixin

from .forms import BesoinForm
from .models import Besoin


class BesoinMixin(ProjetCourantMixin):
    model = Besoin
    onglet = "besoins"

    def get_success_url(self):
        return reverse("besoin_list", args=[self.projet.pk])


class BesoinListView(BesoinMixin, ListView):
    template_name = "besoin/besoin_list.html"
    context_object_name = "besoins"

    def get_queryset(self):
        qs = super().get_queryset()
        # Filtres optionnels dans l'URL : ?type=F  ou  ?type=NF
        self.filtre_type = self.request.GET.get("type", "")
        if self.filtre_type in ("F", "NF"):
            qs = qs.filter(type_besoin=self.filtre_type)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtre_type"] = self.filtre_type
        tous = Besoin.objects.filter(projet=self.projet)
        context["nb_total"] = tous.count()
        context["nb_f"] = tous.filter(type_besoin="F").count()
        context["nb_nf"] = tous.filter(type_besoin="NF").count()
        return context


class BesoinDetailView(BesoinMixin, DetailView):
    template_name = "besoin/besoin_detail.html"
    context_object_name = "besoin"


class BesoinCreateView(BesoinMixin, CreateView):
    form_class = BesoinForm
    template_name = "besoin/besoin_form.html"

    def get_initial(self):
        # Pré-remplir le type si on vient de ?type=NF
        return {"type_besoin": self.request.GET.get("type", "F")}

    def form_valid(self, form):
        form.instance.projet = self.projet
        form.instance.source = "manuel"
        messages.success(self.request, "Besoin ajouté.")
        return super().form_valid(form)


class BesoinUpdateView(BesoinMixin, UpdateView):
    form_class = BesoinForm
    template_name = "besoin/besoin_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Besoin modifié.")
        return super().form_valid(form)


class BesoinDeleteView(BesoinMixin, DeleteView):
    template_name = "besoin/besoin_confirm_delete.html"
    context_object_name = "besoin"

    def form_valid(self, form):
        messages.success(self.request, "Besoin supprimé.")
        return super().form_valid(form)
