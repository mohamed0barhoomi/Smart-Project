from django.urls import path

from .views import EstimationDeleteView, EstimationDetailView, EstimationUpdateView

# Toutes ces URLs sont précédées de  projets/<projet_pk>/estimation/  (voir config/urls.py)
# Pas de page « ajouter » : l'estimation est créée par l'IA depuis le chat.
urlpatterns = [
    path("", EstimationDetailView.as_view(), name="estimation_detail"),
    path("modifier/", EstimationUpdateView.as_view(), name="estimation_update"),
    path("supprimer/", EstimationDeleteView.as_view(), name="estimation_delete"),
]
