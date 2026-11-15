import json
import re

from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.db import models
from django.utils import timezone

from UsersApp.models import TimeStampedModel, User


# ---------- règles UML (envoyées à l'éditeur JavaScript et vérifiées à l'enregistrement) ----------
ELEMENT_KIND_CHOICES = [
    ("class", "Class"), ("interface", "Interface"), ("enumeration", "Enumeration"),
    ("actor", "Actor"), ("usecase", "Use case"), ("system", "System boundary"),
]
RELATIONSHIP_TYPE_CHOICES = [
    ("association", "Association"), ("inheritance", "Inheritance"), ("aggregation", "Aggregation"),
    ("composition", "Composition"), ("dependency", "Dependency"), ("include", "Include"),
    ("extend", "Extend"), ("generalization", "Generalization"),
]
ELEMENT_KINDS = {
    "class": ["class", "interface", "enumeration"],
    "usecase": ["actor", "usecase", "system"],
}
RELATIONSHIP_TYPES = {
    "class": ["association", "inheritance", "aggregation", "composition", "dependency"],
    "usecase": ["association", "include", "extend", "generalization"],
}
RELATIONSHIP_ENDPOINTS = {
    "class": {rel: None for rel in RELATIONSHIP_TYPES["class"]},      # None = toutes les paires
    "usecase": {
        "association": [["actor", "usecase"], ["usecase", "actor"]],
        "include": [["usecase", "usecase"]],
        "extend": [["usecase", "usecase"]],
        "generalization": [["actor", "actor"], ["usecase", "usecase"]],
    },
}
KINDS_WITH_ATTRIBUTES = ["class", "interface", "enumeration"]
KINDS_WITH_METHODS = ["class", "interface"]
CARDINALITY_REGEX = r"^(\d+|\*|n)(\.\.(\d+|\*|n))?$"
MAX_ELEMENTS, MAX_RELATIONSHIPS = 300, 600

EDITOR_RULES = {
    "elementKinds": ELEMENT_KINDS,
    "elementKindLabels": dict(ELEMENT_KIND_CHOICES),
    "kindsWithAttributes": KINDS_WITH_ATTRIBUTES,
    "kindsWithMethods": KINDS_WITH_METHODS,
    "visibilities": [("+", "Public"), ("-", "Private"), ("#", "Protected"), ("~", "Package")],
    "relationshipTypes": RELATIONSHIP_TYPES,
    "relationshipLabels": dict(RELATIONSHIP_TYPE_CHOICES),
    "relationshipEndpoints": RELATIONSHIP_ENDPOINTS,
    "nonConnectableKinds": ["system"],
    "cardinalityRegex": CARDINALITY_REGEX,
    "cardinalitySuggestions": ["1", "0..1", "*", "0..*", "1..*"],
}

# ---------- exigences (stockées dans Project.requirements) ----------
FUNCTIONAL = "functional"
NON_FUNCTIONAL = "non_functional"
REQ_TYPE_CHOICES = [(FUNCTIONAL, "Functional"), (NON_FUNCTIONAL, "Non-functional")]
PRIORITY_CHOICES = [("high", "High"), ("medium", "Medium"), ("low", "Low")]
CATEGORY_CHOICES = [
    ("performance", "Performance"),
    ("security", "Security"),
    ("reliability", "Reliability & availability"),
    ("scalability", "Scalability"),
    ("usability", "Usability & accessibility"),
    ("maintainability", "Maintainability"),
    ("compatibility", "Compatibility"),
    ("portability", "Portability"),
    ("data_integrity", "Data integrity"),
    ("privacy", "Privacy"),
]


class Project(TimeStampedModel):
    class ProjectStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    class DiagramType(models.TextChoices):
        CLASS = "class", "Class diagram"
        USE_CASE = "usecase", "Use case diagram"

    title = models.CharField(max_length=120,
                             validators=[MinLengthValidator(2, "The project name must contain at least 2 characters.")])
    description = models.TextField(blank=True,
                                   validators=[MaxLengthValidator(2000, "The description must not exceed 2000 characters.")])
    status = models.CharField(
        max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.DRAFT
    )
    requirements = models.JSONField(default=list, blank=True)
    class_diagram = models.TextField(blank=True)      # diagramme de classes (JSON de l'éditeur)
    use_case_diagram = models.TextField(blank=True)   # diagramme de cas d'utilisation (JSON de l'éditeur)
    diagram_history = models.JSONField(default=list, blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="projects",
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

    # ---------- diagrammes ----------
    @staticmethod
    def field_name(diagram_type):
        return "class_diagram" if diagram_type == "class" else "use_case_diagram"

    def get_diagram(self, diagram_type):
        """Le diagramme (dict) de ce type, ou None s'il n'existe pas."""
        text = getattr(self, self.field_name(diagram_type))
        if not text:
            return None
        return {**json.loads(text), "diagram_type": diagram_type,
                "get_diagram_type_display": self.DiagramType(diagram_type).label}

    def set_diagram(self, diagram_type, data):
        """Enregistre le diagramme dans son champ (None le supprime)."""
        text = ""
        if data is not None:
            data = {k: v for k, v in data.items() if k not in ("diagram_type", "get_diagram_type_display")}
            text = json.dumps({**data, "updated_at": timezone.now().isoformat()})
        setattr(self, self.field_name(diagram_type), text)

    def diagrams(self):
        return [d for d in (self.get_diagram("class"), self.get_diagram("usecase")) if d]

    @property
    def class_count(self):
        return int(bool(self.class_diagram))

    @property
    def usecase_count(self):
        return int(bool(self.use_case_diagram))

    @property
    def diagram_count(self):
        return self.class_count + self.usecase_count

    # ---------- exigences ----------
    def get_requirement(self, code):
        return next((r for r in self.requirements if r["code"] == code), None)

    def next_code(self, req_type):
        prefix = "FR" if req_type == FUNCTIONAL else "NFR"
        numbers = [int(r["code"].split("-")[1]) for r in self.requirements
                   if re.fullmatch(rf"{prefix}-\d{{3,}}", r["code"])]
        return f"{prefix}-{max(numbers, default=0) + 1:03d}"


def validate_diagram(diagram_type, data):
    """Vérifie le contenu envoyé par l'éditeur avec les règles UML. Retourne (éléments, relations) nettoyés."""
    if not isinstance(data, dict):
        raise ValidationError("Invalid diagram data.")
    elements, relationships = data.get("elements", []), data.get("relationships", [])
    if not isinstance(elements, list) or not isinstance(relationships, list):
        raise ValidationError("'elements' and 'relationships' must be lists.")
    if len(elements) > MAX_ELEMENTS:
        raise ValidationError(f"A diagram cannot contain more than {MAX_ELEMENTS} elements.")
    if len(relationships) > MAX_RELATIONSHIPS:
        raise ValidationError(f"A diagram cannot contain more than {MAX_RELATIONSHIPS} relationships.")

    def text(item, key, default=""):
        value = item.get(key, default)
        if value is None:
            return default
        if not isinstance(value, str):
            raise ValidationError(f"'{key}' must be a string.")
        return value.strip()

    def number(item, key, default):
        value = item.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or abs(value) > 100_000:
            raise ValidationError(f"'{key}' must be a number.")
        return value

    def check(condition, message):
        if not condition:
            raise ValidationError(message)

    clean_elements, kinds, classifier_names = [], {}, set()
    for index, el in enumerate(elements):
        check(isinstance(el, dict), f"Element #{index + 1} is invalid.")
        el_id, kind, name = str(el.get("id") or f"_{index}"), text(el, "kind"), text(el, "name")
        label = f"Element '{name or index + 1}'"
        check(el_id not in kinds, f"Duplicate element id '{el_id}'.")
        check(name, f"{label}: The name is required.")
        check(kind in ELEMENT_KINDS[diagram_type], f"{label}: A {kind} cannot be placed in this diagram.")
        if kind in KINDS_WITH_ATTRIBUTES:
            check(name.lower() not in classifier_names,
                  f"{label}: A classifier named '{name}' already exists in this diagram.")
            classifier_names.add(name.lower())
        width, height = number(el, "width", 160), number(el, "height", 80)
        check(width > 0 and height > 0, f"{label}: Width and height must be positive.")
        attributes = [{"name": text(a, "name"), "data_type": text(a, "data_type"),
                       "visibility": text(a, "visibility", "-") or "-"} for a in el.get("attributes", [])]
        methods = [{"name": text(m, "name"), "parameters": text(m, "parameters"),
                    "return_type": text(m, "return_type"),
                    "visibility": text(m, "visibility", "+") or "+"} for m in el.get("methods", [])]
        check(not attributes or kind in KINDS_WITH_ATTRIBUTES, f"{label}: A {kind} cannot have attributes.")
        check(not methods or kind in KINDS_WITH_METHODS, f"{label}: A {kind} cannot have methods.")
        check(all(item["name"] for item in attributes + methods),
              f"{label}: Attribute and method names are required.")
        kinds[el_id] = (kind, name)
        clean_elements.append({
            "id": el_id, "kind": kind, "name": name, "description": text(el, "description"),
            "x": number(el, "x", 0), "y": number(el, "y", 0), "width": width, "height": height,
            "attributes": attributes, "methods": methods,
        })

    clean_relationships = []
    for index, rel in enumerate(relationships):
        check(isinstance(rel, dict), f"Relationship #{index + 1} is invalid.")
        source, target = str(rel.get("source")), str(rel.get("target"))
        check(source in kinds and target in kinds,
              f"Relationship #{index + 1}: source or target element does not exist.")
        (source_kind, source_name), (target_kind, target_name) = kinds[source], kinds[target]
        label = f"Relationship {source_name} → {target_name}"
        rel_type = text(rel, "rel_type")
        check(source != target, f"{label}: An element cannot be connected to itself.")
        check(rel_type in RELATIONSHIP_TYPES[diagram_type], f"{label}: '{rel_type}' is not allowed in this diagram type.")
        check("system" not in (source_kind, target_kind), f"{label}: A system boundary cannot be connected.")
        pairs = RELATIONSHIP_ENDPOINTS[diagram_type][rel_type]
        check(pairs is None or [source_kind, target_kind] in pairs,
              f"{label}: A {rel_type} cannot link a {source_kind} to a {target_kind}.")
        cardinalities = [text(rel, "source_cardinality"), text(rel, "target_cardinality")]
        check(all(not c or re.fullmatch(CARDINALITY_REGEX, c) for c in cardinalities),
              f"{label}: Invalid cardinality (examples: 1, 0..1, *, 0..*, 1..*).")
        check(diagram_type == "class" or not any(cardinalities),
              f"{label}: Cardinalities are only used in class diagrams.")
        clean_relationships.append({
            "id": str(rel.get("id") or f"r{index}"), "source": source, "target": target,
            "rel_type": rel_type, "label": text(rel, "label"),
            "source_cardinality": cardinalities[0], "target_cardinality": cardinalities[1],
        })
    return clean_elements, clean_relationships


class ProjectAccess(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REFUSED = "refused", "Refused"

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="accesses",
    )
    company = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="project_accesses",
        limit_choices_to={"role": User.UserRole.COMPANY},
    )

    def __str__(self):
        return f"{self.company.email} → {self.project.title} ({self.get_status_display()})"


class Conversation(TimeStampedModel):
    messages = models.JSONField(default=list, blank=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="conversations",
    )

    def __str__(self):
        return f"Conversation {self.pk} : {self.project.title}"
