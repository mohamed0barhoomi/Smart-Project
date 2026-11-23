from django.urls import path

from .views import BesoinCreateView, BesoinDeleteView, BesoinDetailView, BesoinListView, BesoinUpdateView

# Toutes ces URLs sont précédées de  projets/<projet_pk>/besoins/  (voir config/urls.py)
urlpatterns = [
    path("", BesoinListView.as_view(), name="besoin_list"),
    path("<int:pk>/", BesoinDetailView.as_view(), name="besoin_detail"),
    path("ajouter/", BesoinCreateView.as_view(), name="besoin_create"),
    path("modifier/<int:pk>/", BesoinUpdateView.as_view(), name="besoin_update"),
    path("supprimer/<int:pk>/", BesoinDeleteView.as_view(), name="besoin_delete"),
]
