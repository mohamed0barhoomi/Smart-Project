from django.urls import path

from .views import ProjetCreateView, ProjetDeleteView, ProjetDetailView, ProjetListView, ProjetUpdateView

urlpatterns = [
    path("", ProjetListView.as_view(), name="projet_list"),
    path("<int:pk>/", ProjetDetailView.as_view(), name="projet_detail"),
    path("ajouter/", ProjetCreateView.as_view(), name="projet_create"),
    path("modifier/<int:pk>/", ProjetUpdateView.as_view(), name="projet_update"),
    path("supprimer/<int:pk>/", ProjetDeleteView.as_view(), name="projet_delete"),
]
