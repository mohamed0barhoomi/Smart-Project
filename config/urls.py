from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    # La page d'accueil redirige vers la liste des projets
    path("", RedirectView.as_view(pattern_name="projet_list"), name="accueil"),
    path("compte/", include("Compte_App.urls")),
    path("projets/", include("Projet_App.urls")),
    # Le chat, les besoins et les diagrammes appartiennent toujours à un projet,
    # donc leurs URLs commencent par projets/<id du projet>/...
    path("projets/<int:projet_pk>/chat/", include("Chat_App.urls")),
    path("projets/<int:projet_pk>/besoins/", include("Besoin_App.urls")),
    path("projets/<int:projet_pk>/diagrammes/", include("Diagramme_App.urls")),
]
