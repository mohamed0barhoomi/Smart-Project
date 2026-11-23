from django.urls import path

from .views import chat, generer, vider_chat

# Précédées de  projets/<projet_pk>/chat/
urlpatterns = [
    path("", chat, name="chat"),
    path("generer/", generer, name="generer"),
    path("vider/", vider_chat, name="vider_chat"),
]
