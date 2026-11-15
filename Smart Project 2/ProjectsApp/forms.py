from django import forms
from .models import Project, PRIORITY_CHOICES, CATEGORY_CHOICES


class ProjectForm(forms.ModelForm):

    class Meta:
        model = Project
        fields = ["title", "description"]

        labels = {"title": "Project name"}
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Library management system", "autofocus": True}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "What is this project about? Who will use it?"}),
        }


class DiagramForm(forms.Form):
    """Création manuelle : titre, description et type du diagramme."""
    title = forms.CharField(min_length=2, max_length=120,
                            widget=forms.TextInput(attrs={"placeholder": "e.g. Domain model", "autofocus": True}),
                            error_messages={"min_length": "The title must contain at least 2 characters."})
    description = forms.CharField(required=False, max_length=1000,
                                  widget=forms.Textarea(attrs={"rows": 3, "placeholder": "What does this diagram describe? (optional)"}))
    diagram_type = forms.ChoiceField(choices=Project.DiagramType.choices, widget=forms.RadioSelect,
                                     initial=Project.DiagramType.CLASS)


class DiagramRenameForm(forms.Form):
    """Modification : le type ne change pas."""
    title = forms.CharField(min_length=2, max_length=120,
                            error_messages={"min_length": "The title must contain at least 2 characters."})
    description = forms.CharField(required=False, max_length=1000,
                                  widget=forms.Textarea(attrs={"rows": 3}))


class GenerateForm(forms.Form):
    """Interface du chatbot (désactivé)."""
    diagram_type = forms.ChoiceField(choices=Project.DiagramType.choices, widget=forms.RadioSelect,
                                     initial=Project.DiagramType.CLASS)


class RequirementForm(forms.Form):
    title = forms.CharField(min_length=3, max_length=160,
                            error_messages={"min_length": "The title must contain at least 3 characters."})
    description = forms.CharField(max_length=3000, widget=forms.Textarea(attrs={"rows": 3}))
    actor = forms.CharField(required=False, max_length=120)
    module = forms.CharField(required=False, max_length=120, label="Module / functionality")
    category = forms.ChoiceField(required=False, choices=[("", "---------")] + CATEGORY_CHOICES)
    priority = forms.ChoiceField(choices=PRIORITY_CHOICES, initial="medium")
    acceptance_criteria = forms.CharField(required=False, help_text="One criterion per line.",
                                          widget=forms.Textarea(attrs={"rows": 3, "placeholder": "One criterion per line"}))
    needs_confirmation = forms.BooleanField(required=False, label="Proposed target to be confirmed",
                                            help_text="Proposed target that the stakeholders must confirm.")

    def __init__(self, *args, req_type="functional", **kwargs):
        super().__init__(*args, **kwargs)
        self.req_type = req_type

    def clean(self):
        cleaned_data = super().clean()
        if self.req_type == "non_functional":
            if not cleaned_data.get("category"):
                self.add_error("category", "Choose a category for a non-functional requirement.")
            cleaned_data["actor"] = cleaned_data["module"] = ""
        else:
            cleaned_data["category"] = ""
        return cleaned_data
