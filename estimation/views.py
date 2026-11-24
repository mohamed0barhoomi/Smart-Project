from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EstimationForm
from .models import Estimation, Projet

# Accès réservé aux administrateurs connectés
admin_requis = user_passes_test(
    lambda u: u.is_authenticated and u.is_staff,
    login_url='connexion',
)


# ---------- READ : dashboard ----------
@admin_requis
def dashboard(request):
    estimations = Estimation.objects.select_related('projet')
    totaux = estimations.aggregate(cout_total=Sum('cout'), delai_moyen=Avg('delai'))
    context = {
        'estimations': estimations,
        'nb_estimations': estimations.count(),
        'nb_sans_estimation': Projet.objects.filter(estimation__isnull=True).count(),
        'cout_total': totaux['cout_total'] or 0,
        'delai_moyen': totaux['delai_moyen'] or 0,
        # Données des graphiques (float : Chart.js attend des nombres)
        'labels': [e.projet.nom for e in estimations],
        'couts': [float(e.cout) for e in estimations],
        'delais': [float(e.delai) for e in estimations],
    }
    return render(request, 'estimation/dashboard.html', context)


# ---------- UPDATE / DELETE ----------
# Pas de vue « ajouter » : comme dans SmartProjects, l'estimation est créée par l'IA.
# Un projet a une seule estimation : on la retrouve à partir de l'id du projet.

@admin_requis
def modifier_estimation(request, projet_pk):
    estimation = get_object_or_404(Estimation, projet_id=projet_pk)
    form = EstimationForm(request.POST or None, instance=estimation)
    if form.is_valid():
        form.save()
        messages.success(request, "Estimation modifiée.")
        return redirect('dashboard')
    return render(request, 'estimation/form.html',
                  {'form': form, 'titre': f"Modifier l'estimation — {estimation.projet.nom}"})


@admin_requis
def supprimer_estimation(request, projet_pk):
    estimation = get_object_or_404(Estimation, projet_id=projet_pk)
    if request.method == 'POST':
        estimation.delete()
        messages.success(request, "Estimation supprimée.")
        return redirect('dashboard')
    return render(request, 'estimation/confirmer_suppression.html',
                  {'objet': estimation})
