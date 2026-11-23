from django import forms

from .models import Diagramme


class DiagrammeForm(forms.ModelForm):
    class Meta:
        model = Diagramme
        fields = ["type_diagramme", "titre", "code_plantuml"]
        widgets = {
            # id="editeur" : utilisé par le petit script d'aperçu en direct dans le template
            "code_plantuml": forms.Textarea(attrs={"rows": 18, "id": "editeur", "spellcheck": "false"}),
        }

    def clean_code_plantuml(self):
        code = self.cleaned_data["code_plantuml"].strip()
        # Un code PlantUML valide commence par @startuml et finit par @enduml
        if not code.startswith("@startuml"):
            raise forms.ValidationError("Le code doit commencer par @startuml.")
        if not code.endswith("@enduml"):
            raise forms.ValidationError("Le code doit se terminer par @enduml.")
        return code
