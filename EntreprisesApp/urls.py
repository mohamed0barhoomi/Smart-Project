from django.urls import path

from .views import (createEntreprise, deleteEntreprise, detailEntreprise,
                    listEntreprises, updateEntreprise)

app_name = "entreprise"

urlpatterns = [
    path('', listEntreprises, name='entreprise_list'),
    path('ajouter/', createEntreprise, name='entreprise_create'),
    path('<int:pk>/', detailEntreprise, name='entreprise_detail'),
    path('<int:pk>/modifier/', updateEntreprise, name='entreprise_update'),
    path('<int:pk>/supprimer/', deleteEntreprise, name='entreprise_delete'),
]