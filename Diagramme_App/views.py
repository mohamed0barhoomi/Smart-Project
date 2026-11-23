import json                                                     # export : écriture du fichier JSON

from django.contrib import messages
from django.http import Http404, HttpResponse, JsonResponse      # export : réponses « fichier » et erreurs
from django.shortcuts import redirect                            # export : retour à la page en cas d'erreur
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from Projet_App.mixins import ProjetCourantMixin

from .export import ErreurExport, exporter_json, exporter_pdf, exporter_svg, nom_fichier   # export : fonctions de conversion
from .forms import DiagrammeForm
from .models import Diagramme

# Modèles de départ proposés quand on crée un diagramme à la main
MODELE_USECASE = """@startuml
left to right direction
actor Utilisateur
rectangle "Système" {
  Utilisateur --> (Se connecter)
}
@enduml"""

MODELE_CLASSE = """@startuml
class Utilisateur {
  - id : int
  - nom : String
  + seConnecter()
}
@enduml"""


class DiagrammeMixin(ProjetCourantMixin):
    model = Diagramme
    onglet = "diagrammes"

    def get_success_url(self):
        return reverse("diagramme_detail", args=[self.projet.pk, self.object.pk])


class DiagrammeListView(DiagrammeMixin, ListView):
    template_name = "diagramme/diagramme_list.html"
    context_object_name = "diagrammes"


class DiagrammeDetailView(DiagrammeMixin, DetailView):
    template_name = "diagramme/diagramme_detail.html"
    context_object_name = "diagramme"


class DiagrammeCreateView(DiagrammeMixin, CreateView):
    form_class = DiagrammeForm
    template_name = "diagramme/diagramme_form.html"

    def get_initial(self):
        type_diagramme = self.request.GET.get("type", "usecase")
        code = MODELE_CLASSE if type_diagramme == "classe" else MODELE_USECASE
        return {"type_diagramme": type_diagramme, "code_plantuml": code}

    def form_valid(self, form):
        form.instance.projet = self.projet
        form.instance.source = "manuel"
        messages.success(self.request, "Diagramme créé.")
        return super().form_valid(form)


class DiagrammeUpdateView(DiagrammeMixin, UpdateView):
    form_class = DiagrammeForm
    template_name = "diagramme/diagramme_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Diagramme enregistré.")
        return super().form_valid(form)


class DiagrammeDeleteView(DiagrammeMixin, DeleteView):
    template_name = "diagramme/diagramme_confirm_delete.html"
    context_object_name = "diagramme"

    def get_success_url(self):
        return reverse("diagramme_list", args=[self.projet.pk])

    def form_valid(self, form):
        messages.success(self.request, "Diagramme supprimé.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Export d'un diagramme (bouton « Export Diagram » de la page de détail)
# ---------------------------------------------------------------------------

# Pour chaque format : fonction qui produit le contenu + type MIME du fichier   # export : formats proposés dans le menu
FORMATS_EXPORT = {
    "pdf": (exporter_pdf, "application/pdf"),                    # document PDF à la taille du diagramme
    "svg": (exporter_svg, "image/svg+xml"),                      # image vectorielle
    "json": (exporter_json, "application/json; charset=utf-8"),  # données structurées du diagramme
}


class DiagrammeExportView(DiagrammeMixin, DetailView):           # export : DiagrammeMixin vérifie que le projet appartient à l'utilisateur
    """Renvoie le diagramme sous forme de fichier à télécharger (PDF, SVG ou JSON)."""

    def get(self, request, *args, **kwargs):                     # export : uniquement des requêtes GET (lecture seule)
        format_export = kwargs["format_export"]                  # "pdf", "svg" ou "json" (vient de l'URL)
        if format_export not in FORMATS_EXPORT:                  # format inconnu -> page 404
            raise Http404("Format d'export inconnu.")
        diagramme = self.get_object()                            # 404 si le diagramme n'est pas dans ce projet
        fonction, type_mime = FORMATS_EXPORT[format_export]      # fonction de conversion à utiliser

        try:
            contenu = fonction(diagramme)                        # production du fichier (peut appeler le serveur PlantUML)
        except ErreurExport as e:                                # erreur prévue : réseau, syntaxe PlantUML...
            return self.erreur(request, diagramme, str(e))
        except Exception as e:                                   # erreur imprévue : on n'affiche pas de page d'erreur 500
            print(f"[Export] erreur inattendue ({format_export}) -> {e}")   # visible dans le terminal runserver
            return self.erreur(request, diagramme, "une erreur inattendue est survenue.")

        if format_export == "json":                              # le dictionnaire Python devient un texte JSON indenté
            contenu = json.dumps(contenu, ensure_ascii=False, indent=2)
        reponse = HttpResponse(contenu, content_type=type_mime)  # le fichier lui-même
        nom = nom_fichier(diagramme, format_export)              # ex : test_class_diagram.pdf
        reponse["Content-Disposition"] = f'attachment; filename="{nom}"'   # « attachment » = téléchargement
        return reponse

    def erreur(self, request, diagramme, message):               # export : réponse commune en cas d'échec
        if request.headers.get("x-requested-with") == "XMLHttpRequest":   # appel fait par le JavaScript du menu
            return JsonResponse({"erreur": message}, status=502)  # le JavaScript affiche le message
        messages.error(request, f"L'export a échoué : {message}")  # sans JavaScript : message flash habituel
        return redirect("diagramme_detail", self.projet.pk, diagramme.pk)
