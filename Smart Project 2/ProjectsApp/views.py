import json
from datetime import datetime

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import CreateView, ListView, DeleteView, DetailView, UpdateView

from UsersApp.models import User
from .forms import ProjectForm, DiagramForm, DiagramRenameForm, GenerateForm, RequirementForm
from .models import (
    Project, validate_diagram, EDITOR_RULES,
    ELEMENT_KINDS, ELEMENT_KIND_CHOICES, RELATIONSHIP_TYPES, RELATIONSHIP_TYPE_CHOICES,
    FUNCTIONAL, NON_FUNCTIONAL, REQ_TYPE_CHOICES, PRIORITY_CHOICES, CATEGORY_CHOICES,
)
from .pdf import build_srs_pdf

SORT_OPTIONS = {
    "updated": ("-updated_at", "Last modified"),
    "created": ("-created_at", "Newest first"),
    "oldest": ("created_at", "Oldest first"),
    "name": ("title", "Name (A–Z)"),
}
ELEMENT_SHORTCUTS = {"class": "C", "interface": "I", "enumeration": "E",
                     "actor": "A", "usecase": "U", "system": "B"}


# ---------- fonctions utiles ----------

def render_page(request, template, context):
    """render() avec les derniers projets de la barre latérale."""
    return render(request, template, {**context, "sidebar_projects": Project.objects.all()[:5]})


class SidebarMixin:
    """Ajoute les derniers projets de la barre latérale aux vues classes."""
    def get_context_data(self,**kwargs):
        return super().get_context_data(sidebar_projects=Project.objects.all()[:5], **kwargs)


def next_url(request, default):
    url = request.POST.get("next") or request.GET.get("next")
    if url and url_has_allowed_host_and_scheme(url, {request.get_host()}, request.is_secure()):
        return url
    return default


def get_diagram_or_404(project, diagram_type):
    diagram = project.get_diagram(diagram_type) if diagram_type in ELEMENT_KINDS else None
    if diagram is None:
        raise Http404("This diagram does not exist.")
    return diagram


def get_requirement_or_404(pk, code):
    project = get_object_or_404(Project, pk=pk)
    requirement = project.get_requirement(code)
    if requirement is None:
        raise Http404("This requirement does not exist.")
    return project, requirement


def diagram_preview(diagram):
    """Miniature SVG du diagramme (cartes du projet)."""
    elements = diagram["elements"]
    if not elements:
        return {"empty": True}
    padding = 24
    min_x = min(e["x"] for e in elements) - padding
    min_y = min(e["y"] for e in elements) - padding
    width = max(e["x"] + e["width"] for e in elements) + padding - min_x
    height = max(e["y"] + e["height"] for e in elements) + padding - min_y
    if width / height > 2.4:                 # garder des proportions agréables pour la carte
        min_y -= (width / 2.4 - height) / 2
        height = width / 2.4
    elif width / height < 1.2:
        min_x -= (height * 1.2 - width) / 2
        width = height * 1.2
    by_id = {e["id"]: e for e in elements}
    lines = [{"x1": s["x"] + s["width"] / 2, "y1": s["y"] + s["height"] / 2,
              "x2": t["x"] + t["width"] / 2, "y2": t["y"] + t["height"] / 2,
              "dashed": rel["rel_type"] in ("dependency", "include", "extend")}
             for rel in diagram["relationships"]
             for s, t in [(by_id.get(rel["source"]), by_id.get(rel["target"]))] if s and t]
    shapes = [{"kind": e["kind"], "x": e["x"], "y": e["y"], "w": e["width"], "h": e["height"],
               "cx": e["x"] + e["width"] / 2, "cy": e["y"] + e["height"] / 2,
               "rx": e["width"] / 2, "ry": e["height"] / 2,
               "header": e["y"] + min(30, e["height"]), "x2": e["x"] + e["width"],
               "head_cy": e["y"] + 14, "body1": e["y"] + 26, "body2": e["y"] + 58}
              for e in sorted(elements, key=lambda el: el["kind"] != "system")]     # cadres derrière
    return {"empty": False, "viewbox": f"{min_x:.0f} {min_y:.0f} {width:.0f} {height:.0f}",
            "shapes": shapes, "lines": lines}


def requirement_rows(project):
    """Les exigences du projet triées, avec les libellés affichés."""
    categories, priorities = dict(CATEGORY_CHOICES), dict(PRIORITY_CHOICES)
    return sorted(({**r,
                    "category_display": categories.get(r["category"], ""),
                    "priority_display": priorities.get(r["priority"], ""),
                    "criteria_list": [c.strip(" -•\t") for c in r["acceptance_criteria"].splitlines() if c.strip(" -•\t")]}
                   for r in project.requirements),
                  key=lambda r: (r["req_type"], r["code"]))


def section_url(project_pk, tab=FUNCTIONAL):
    return reverse("project:details", args=[project_pk]) + f"?req={tab}#requirements"


# ---------- vues classes : projets ----------

class Project_list(SidebarMixin, ListView):
    model = Project
    template_name = "Project/home.html"
    context_object_name = "projects"

    def get_queryset(self):
        queryset = Project.objects.all()
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))
        content = self.request.GET.get("content", "")
        if content == "class":
            queryset = queryset.exclude(class_diagram="")
        elif content == "usecase":
            queryset = queryset.exclude(use_case_diagram="")
        elif content == "empty":
            queryset = queryset.filter(class_diagram="", use_case_diagram="")
        sort = self.request.GET.get("sort", "updated")
        return queryset.order_by(SORT_OPTIONS.get(sort, SORT_OPTIONS["updated"])[0])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET
        class_count = Project.objects.exclude(class_diagram="").count()
        usecase_count = Project.objects.exclude(use_case_diagram="").count()
        context.update({
            "stats": {
                "projects": Project.objects.count(),
                "diagrams": class_count + usecase_count,
                "class": class_count,
                "usecase": usecase_count,
                "generated": 0,                 # le chatbot est désactivé
            },
            "q": params.get("q", "").strip(),
            "current_content": params.get("content", ""),
            "current_sort": params.get("sort") if params.get("sort") in SORT_OPTIONS else "updated",
            "sort_options": [(key, label) for key, (_, label) in SORT_OPTIONS.items()],
            "has_filters": bool(params.get("q") or params.get("content")),
            "form": ProjectForm(),
        })
        return context


class Project_detail(SidebarMixin, DetailView):
    model = Project
    template_name = "Project/details.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        all_diagrams = project.diagrams()
        for d in all_diagrams:
            d["created"] = datetime.fromisoformat(d["created_at"]) if d.get("created_at") else None
            d["updated"] = datetime.fromisoformat(d["updated_at"]) if d.get("updated_at") else None
            d["preview"] = diagram_preview(d)
        current_type = self.request.GET.get("type", "")
        requirements = requirement_rows(project)
        functional = [r for r in requirements if r["req_type"] == FUNCTIONAL]
        non_functional = [r for r in requirements if r["req_type"] == NON_FUNCTIONAL]
        tab = self.request.GET.get("req")
        context.update({
            "diagrams": [d for d in all_diagrams if current_type not in ELEMENT_KINDS or d["diagram_type"] == current_type],
            "current_type": current_type,
            "counts": {"all": len(all_diagrams), "class": project.class_count,
                       "usecase": project.usecase_count, "generated": 0},
            "generate_form": GenerateForm(),
            "diagram_form": DiagramForm(),
            "req": {
                "functional": functional,
                "non_functional": non_functional,
                "tab": tab if tab in (FUNCTIONAL, NON_FUNCTIONAL) else FUNCTIONAL,
                "priorities": PRIORITY_CHOICES,
                "to_confirm": sum(r["needs_confirmation"] for r in non_functional),
                "uml_text": bool(functional),
            },
            "sidebar_active_project": project.pk,
        })
        return context


class Project_create(SidebarMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "Project/form.html"

    def form_valid(self, form):
        # propriétaire : l'utilisateur connecté, sinon le premier administrateur
        owner = self.request.user if self.request.user.is_authenticated else \
            User.objects.filter(is_superuser=True).order_by("pk").first()
        if owner is None:
            form.add_error(None, "Create an administrator account first: python manage.py createsuperuser")
            return self.form_invalid(form)
        form.instance.user = owner
        messages.success(self.request, f"Project “{form.instance.title}” created. Choose a diagram type to start.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("project:details", args=[self.object.pk])


class Project_update(SidebarMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "Project/form.html"
    context_object_name = "project"

    def form_valid(self, form):
        messages.success(self.request, f"Project “{form.instance.title}” updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return next_url(self.request, reverse("project:details", args=[self.object.pk]))


class Project_delete(SidebarMixin, DeleteView):
    model = Project
    template_name = "Project/confirm_delete.html"
    context_object_name = "project"
    success_url = reverse_lazy("project:list")

    def form_valid(self, form):
        messages.success(self.request, f"Project “{self.object.title}” and its diagrams were deleted.")
        return super().form_valid(form)


# ---------- vues fonctions : diagrammes ----------

def diagram_create(request, pk):
    project = get_object_or_404(Project, pk=pk)
    initial_type = request.GET.get("type") if request.GET.get("type") in ELEMENT_KINDS else "class"
    form = DiagramForm(request.POST or None, initial={"diagram_type": initial_type})
    if not form.is_valid():
        return render_page(request, "Diagram/form.html", {"form": form, "project": project})
    diagram_type, title = form.cleaned_data["diagram_type"], form.cleaned_data["title"]
    if project.get_diagram(diagram_type):
        messages.info(request, f"This project already has a {Project.DiagramType(diagram_type).label.lower()}. "
                               "It is open in the editor.")
    else:
        project.set_diagram(diagram_type, {"title": title, "description": form.cleaned_data["description"],
                                           "source": "manual", "created_at": timezone.now().isoformat(),
                                           "elements": [], "relationships": []})
        project.save()
        messages.success(request, f"Diagram “{title}” created.")
    return redirect("project:diagram_editor", pk=project.pk, diagram_type=diagram_type)


def diagram_editor(request, pk, diagram_type):
    project = get_object_or_404(Project, pk=pk)
    diagram = get_diagram_or_404(project, diagram_type)
    kind_labels, rel_labels = dict(ELEMENT_KIND_CHOICES), dict(RELATIONSHIP_TYPE_CHOICES)
    return render(request, "Diagram/editor.html", {
        "project": project,
        "diagram": diagram,
        "toolbox_elements": [(kind, kind_labels[kind], ELEMENT_SHORTCUTS[kind]) for kind in ELEMENT_KINDS[diagram_type]],
        "toolbox_relationships": [(rel, rel_labels[rel], str(index))
                                  for index, rel in enumerate(RELATIONSHIP_TYPES[diagram_type], start=1)],
        "diagram_data": {
            "id": f"{project.pk}-{diagram_type}",
            "title": diagram["title"],
            "description": diagram.get("description", ""),
            "diagram_type": diagram_type,
            "source": diagram.get("source", "manual"),
            "updated_at": diagram.get("updated_at", ""),
            "elements": diagram["elements"],
            "relationships": diagram["relationships"],
        },
        "editor_config": {
            "apiUrl": reverse("project:diagram_api", args=[project.pk, diagram_type]),
            "deleteUrl": reverse("project:diagram_delete", args=[project.pk, diagram_type]),
            "projectUrl": reverse("project:details", args=[project.pk]),
            "canEdit": True,
            "canDelete": True,
            "rules": EDITOR_RULES,
        },
    })


def diagram_update(request, pk, diagram_type):
    project = get_object_or_404(Project, pk=pk)
    diagram = get_diagram_or_404(project, diagram_type)
    form = DiagramRenameForm(request.POST or None, initial=diagram)
    if not form.is_valid():
        return render_page(request, "Diagram/form.html", {"form": form, "project": project, "diagram": diagram})
    diagram.update(form.cleaned_data)
    project.set_diagram(diagram_type, diagram)
    project.save()
    messages.success(request, f"Diagram “{diagram['title']}” updated.")
    return redirect(next_url(request, reverse("project:details", args=[project.pk])))


def diagram_delete(request, pk, diagram_type):
    project = get_object_or_404(Project, pk=pk)
    diagram = get_diagram_or_404(project, diagram_type)
    if request.method != "POST":
        return render_page(request, "Diagram/confirm_delete.html", {"project": project, "diagram": diagram})
    project.set_diagram(diagram_type, None)
    project.save()
    messages.success(request, f"Diagram “{diagram['title']}” deleted.")
    return redirect("project:details", pk=project.pk)


@require_http_methods(["GET", "PUT"])
def diagram_api(request, pk, diagram_type):
    """Lecture / enregistrement automatique du diagramme par l'éditeur (JSON)."""
    project = get_object_or_404(Project, pk=pk)
    diagram = get_diagram_or_404(project, diagram_type)
    if request.method == "GET":
        return JsonResponse(diagram)
    try:
        data = json.loads(request.body or b"{}")
        elements, relationships = validate_diagram(diagram_type, data)
        title = (data.get("title", diagram["title"]) or "").strip()
        if len(title) < 2:
            raise ValidationError("Diagram: The title must contain at least 2 characters.")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"errors": ["Invalid JSON."]}, status=400)
    except ValidationError as error:
        return JsonResponse({"errors": error.messages}, status=400)

    diagram.update(title=title[:120], elements=elements, relationships=relationships,
                   description=(data.get("description", diagram.get("description", "")) or "").strip())
    project.set_diagram(diagram_type, diagram)
    project.save()
    diagram = project.get_diagram(diagram_type)
    return JsonResponse({"ok": True, "title": diagram["title"], "description": diagram["description"],
                         "updated_at": diagram["updated_at"]})


# ---------- vues fonctions : exigences ----------

def requirement_form_page(request, project, form, req_type, requirement=None):
    return render_page(request, "Requirement/form.html", {
        "form": form, "project": project, "requirement": requirement,
        "req_type": req_type, "req_type_label": dict(REQ_TYPE_CHOICES)[req_type],
    })


def requirement_create(request, pk):
    project = get_object_or_404(Project, pk=pk)
    req_type = request.GET.get("type") or request.POST.get("req_type")
    if req_type not in dict(REQ_TYPE_CHOICES):
        req_type = FUNCTIONAL
    form = RequirementForm(request.POST or None, req_type=req_type)
    if not form.is_valid():
        return requirement_form_page(request, project, form, req_type)
    now = timezone.now().isoformat()
    code = project.next_code(req_type)
    project.requirements.append({"code": code, "req_type": req_type, **form.cleaned_data,
                                 "source": "manual", "is_modified": False, "created_at": now, "updated_at": now})
    project.save()
    messages.success(request, f"Requirement {code} added.")
    return redirect(section_url(project.pk, req_type))


def requirement_update(request, pk, code):
    project, requirement = get_requirement_or_404(pk, code)
    form = RequirementForm(request.POST or None, initial=requirement, req_type=requirement["req_type"])
    if not form.is_valid():
        return requirement_form_page(request, project, form, requirement["req_type"], requirement)
    requirement.update(form.cleaned_data, updated_at=timezone.now().isoformat())
    project.save()
    messages.success(request, f"Requirement {code} updated.")
    return redirect(section_url(project.pk, requirement["req_type"]))


@require_POST
def requirement_priority(request, pk, code):
    project, requirement = get_requirement_or_404(pk, code)
    priority = request.POST.get("priority")
    if priority in dict(PRIORITY_CHOICES) and priority != requirement["priority"]:
        requirement["priority"] = priority
        project.save()
        messages.success(request, f"{code} priority set to {dict(PRIORITY_CHOICES)[priority]}.")
    return redirect(section_url(project.pk, requirement["req_type"]))


def requirement_delete(request, pk, code):
    project, requirement = get_requirement_or_404(pk, code)
    if request.method != "POST":
        return render_page(request, "Requirement/confirm_delete.html", {"project": project, "requirement": requirement})
    project.requirements.remove(requirement)
    project.save()
    messages.success(request, f"Requirement {code} deleted.")
    return redirect(section_url(project.pk, requirement["req_type"]))


def requirement_export(request, pk):
    project = get_object_or_404(Project, pk=pk)
    response = HttpResponse(build_srs_pdf(project, requirement_rows(project)), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="SRS-{slugify(project.title) or "project"}.pdf"'
    return response
