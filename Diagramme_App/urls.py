from django.urls import path

from .views import (DiagrammeCreateView, DiagrammeDeleteView, DiagrammeDetailView,
                    DiagrammeExportView,  # export : vue de téléchargement PDF / SVG / JSON
                    DiagrammeListView, DiagrammeUpdateView)

# Toutes ces URLs sont précédées de  projets/<projet_pk>/diagrammes/
urlpatterns = [
    path("", DiagrammeListView.as_view(), name="diagramme_list"),
    path("<int:pk>/", DiagrammeDetailView.as_view(), name="diagramme_detail"),
    path("ajouter/", DiagrammeCreateView.as_view(), name="diagramme_create"),
    path("modifier/<int:pk>/", DiagrammeUpdateView.as_view(), name="diagramme_update"),
    path("supprimer/<int:pk>/", DiagrammeDeleteView.as_view(), name="diagramme_delete"),
    # export : ex. projets/2/diagrammes/5/export/pdf/  (formats : pdf, svg, json)
    path("<int:pk>/export/<str:format_export>/", DiagrammeExportView.as_view(), name="diagramme_export"),
]
