from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("compte/", include("Compte_App.urls")),
    path("projets/", include("Projet_App.urls")),
    # Le chat, les besoins et les diagrammes appartiennent toujours à un projet,
    # donc leurs URLs commencent par projets/<id du projet>/...
    path("projets/<int:projet_pk>/chat/", include("Chat_App.urls")),
    path("projets/<int:projet_pk>/besoins/", include("Besoin_App.urls")),
    path("projets/<int:projet_pk>/diagrammes/", include("Diagramme_App.urls")),
    # Abonnements : plans, souscription, paiements
    path("abonnements/", include("AbonnementsApp.urls")),
    # Utilisateurs : accueil, connexion, tableau de bord, profil (page d'accueil du site : "")
    path("", include("UtilisateursApp.urls")),
]
