from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from Estimation_App.models import Estimation

from .forms import ProjetForm
from .models import Projet

# LoginRequiredMixin : si l'utilisateur n'est pas connecté, il est redirigé
# vers la page de connexion (settings.LOGIN_URL). Il se place toujours en
# premier dans la liste des classes parentes.


class MesProjetsMixin(LoginRequiredMixin):
    """Mixin = petit morceau de code réutilisé par plusieurs vues.
    Ici : chaque utilisateur ne voit QUE ses propres projets."""

    model = Projet

    def get_queryset(self):
        return Projet.objects.filter(proprietaire=self.request.user)


class ProjetListView(MesProjetsMixin, ListView):
    template_name = "projet/projet_list.html"
    context_object_name = "projets"

    def get_queryset(self):
        qs = super().get_queryset()
        # Petite recherche : /projets/?q=biblio
        recherche = self.request.GET.get("q", "").strip()
        if recherche:
            qs = qs.filter(nom__icontains=recherche)
        return qs


class ProjetDetailView(MesProjetsMixin, DetailView):
    template_name = "projet/projet_detail.html"
    context_object_name = "projet"

    def get_context_data(self, **kwargs):
        # On ajoute des informations en plus dans le template
        context = super().get_context_data(**kwargs)
        projet = self.object
        context["nb_bf"] = projet.besoins.filter(type_besoin="F").count()
        context["nb_bnf"] = projet.besoins.filter(type_besoin="NF").count()
        context["nb_diagrammes"] = projet.diagrammes.count()
        context["nb_messages"] = projet.messages.count()
        context["derniers_besoins"] = projet.besoins.all()[:5]
        context["diagrammes"] = projet.diagrammes.all()
        # None si l'IA n'a pas encore produit d'estimation pour ce projet
        context["estimation"] = Estimation.objects.filter(projet=projet).first()
        context["onglet"] = "apercu"
        return context


class ProjetFormMixin:
    """Partagé par la création et la modification."""

    form_class = ProjetForm
    template_name = "projet/projet_form.html"

    def get_form_kwargs(self):
        # On envoie l'utilisateur au formulaire (voir ProjetForm.__init__)
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ProjetCreateView(LoginRequiredMixin, ProjetFormMixin, CreateView):
    model = Projet

    def form_valid(self, form):
        # Le propriétaire n'est pas dans le formulaire : on le remplit ici.
        form.instance.proprietaire = self.request.user
        messages.success(self.request, "Projet créé. Décrivez-le maintenant dans le chat.")
        return super().form_valid(form)

    def get_success_url(self):
        # Après création, on envoie directement l'utilisateur vers le chat
        return reverse_lazy("chat", args=[self.object.pk])


class ProjetUpdateView(MesProjetsMixin, ProjetFormMixin, UpdateView):
    def form_valid(self, form):
        messages.success(self.request, "Projet mis à jour.")
        return super().form_valid(form)


class ProjetDeleteView(MesProjetsMixin, DeleteView):
    template_name = "projet/projet_confirm_delete.html"
    success_url = reverse_lazy("projet_list")

    def form_valid(self, form):
        messages.success(self.request, f"Le projet « {self.object.nom} » a été supprimé.")
        return super().form_valid(form)
