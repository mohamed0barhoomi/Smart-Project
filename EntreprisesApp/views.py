from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from UtilisateursApp.views import admin_requis, paginer

from .forms import EntrepriseForm
from .models import Entreprise


@admin_requis
def listEntreprises(request):
    return render(request, 'entreprise/entreprise_list.html', {
        "liste": paginer(request, Entreprise.objects.all()),
    })


@admin_requis
def detailEntreprise(request, pk):
    entreprise = get_object_or_404(Entreprise, pk=pk)
    return render(request, 'entreprise/entreprise_detail.html', {"entreprise": entreprise})


@admin_requis
def createEntreprise(request):
    form = EntrepriseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        entreprise = form.save()
        messages.success(request, f"L'entreprise {entreprise.nom} a été ajoutée.")
        return redirect('entreprise:entreprise_list')
    return render(request, 'entreprise/entreprise_form.html', {"form": form})


@admin_requis
def updateEntreprise(request, pk):
    entreprise = get_object_or_404(Entreprise, pk=pk)
    form = EntrepriseForm(request.POST or None, instance=entreprise)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"L'entreprise {entreprise.nom} a été modifiée.")
        return redirect('entreprise:entreprise_list')
    return render(request, 'entreprise/entreprise_form.html', {"form": form, "object": entreprise})


@admin_requis
def deleteEntreprise(request, pk):
    entreprise = get_object_or_404(Entreprise, pk=pk)
    if request.method == "POST":
        nom = entreprise.nom
        entreprise.delete()
        messages.success(request, f"L'entreprise {nom} a été supprimée.")
        return redirect('entreprise:entreprise_list')
    return render(request, 'entreprise/entreprise_delete.html', {"entreprise": entreprise})