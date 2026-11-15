from django.urls import path
from .views import (
    Project_list, Project_detail, Project_create, Project_update, Project_delete,
    diagram_create, diagram_editor, diagram_update, diagram_delete, diagram_api,
    requirement_create, requirement_update, requirement_priority, requirement_delete, requirement_export,
)

app_name = "project"

urlpatterns = [
    path("", Project_list.as_view(), name="list"),
    path("project/create/", Project_create.as_view(), name="create"),
    path("project/<int:pk>/", Project_detail.as_view(), name="details"),
    path("project/<int:pk>/update/", Project_update.as_view(), name="update"),
    path("project/<int:pk>/delete/", Project_delete.as_view(), name="delete"),

    path("project/<int:pk>/diagram/create/", diagram_create, name="diagram_create"),
    path("project/<int:pk>/diagram/<str:diagram_type>/", diagram_editor, name="diagram_editor"),
    path("project/<int:pk>/diagram/<str:diagram_type>/update/", diagram_update, name="diagram_update"),
    path("project/<int:pk>/diagram/<str:diagram_type>/delete/", diagram_delete, name="diagram_delete"),
    path("project/<int:pk>/diagram/<str:diagram_type>/api/", diagram_api, name="diagram_api"),

    path("project/<int:pk>/requirement/create/", requirement_create, name="requirement_create"),
    path("project/<int:pk>/requirement/<str:code>/update/", requirement_update, name="requirement_update"),
    path("project/<int:pk>/requirement/<str:code>/priority/", requirement_priority, name="requirement_priority"),
    path("project/<int:pk>/requirement/<str:code>/delete/", requirement_delete, name="requirement_delete"),
    path("project/<int:pk>/requirement/export/", requirement_export, name="requirement_export"),
]
