from django.test import TestCase
from django.urls import reverse

from UtilisateursApp.models import User

from .models import Entreprise

DONNEES = {
    "nom": "TechCorp",
    "secteur": "Informatique",
    "competences": "Python, Django, SQL",
    "localisation": "Tunis",
    "type_opportunite": "STAGE",
    "description": "",
    "site_web": "https://techcorp.example.com",
}


class EntrepriseCrudTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin1', 'admin1@gmail.com', 'MotDePasse!123', role='ADMIN')
        self.client_user = User.objects.create_user('cli1', 'cli1@gmail.com', 'MotDePasse!123', role='USER')
        self.client.force_login(self.admin)

    # ---- Ajouter
    def test_ajouter_valide(self):
        r = self.client.post(reverse('entreprise:entreprise_create'), DONNEES)
        self.assertRedirects(r, reverse('entreprise:entreprise_list'))
        self.assertEqual(Entreprise.objects.count(), 1)

    def test_ajouter_nom_vide_refuse(self):
        r = self.client.post(reverse('entreprise:entreprise_create'), {**DONNEES, "nom": ""})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Entreprise.objects.count(), 0)

    def test_nom_unique(self):
        Entreprise.objects.create(**DONNEES)
        r = self.client.post(reverse('entreprise:entreprise_create'), DONNEES)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Entreprise.objects.count(), 1)

    def test_site_web_invalide_refuse(self):
        r = self.client.post(reverse('entreprise:entreprise_create'), {**DONNEES, "site_web": "pas-un-lien"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Entreprise.objects.count(), 0)

    # ---- Afficher
    def test_liste_vide_et_remplie(self):
        r = self.client.get(reverse('entreprise:entreprise_list'))
        self.assertContains(r, 'Aucune entreprise')
        Entreprise.objects.create(**DONNEES)
        r = self.client.get(reverse('entreprise:entreprise_list'))
        self.assertContains(r, 'TechCorp')
        self.assertContains(r, 'data-confirm=')       # fenêtre de confirmation de base.html

    def test_detail_et_404(self):
        e = Entreprise.objects.create(**DONNEES)
        self.assertContains(self.client.get(reverse('entreprise:entreprise_detail', args=[e.pk])), 'Django')
        self.assertEqual(self.client.get(reverse('entreprise:entreprise_detail', args=[999])).status_code, 404)

    # ---- Modifier
    def test_modifier(self):
        e = Entreprise.objects.create(**DONNEES)
        r = self.client.get(reverse('entreprise:entreprise_update', args=[e.pk]))
        self.assertContains(r, 'TechCorp')            # formulaire pré-rempli
        r = self.client.post(reverse('entreprise:entreprise_update', args=[e.pk]), {**DONNEES, "localisation": "Sfax"})
        self.assertRedirects(r, reverse('entreprise:entreprise_list'))
        e.refresh_from_db()
        self.assertEqual(e.localisation, "Sfax")

    def test_modifier_sans_changer_le_nom_est_accepte(self):
        e = Entreprise.objects.create(**DONNEES)
        r = self.client.post(reverse('entreprise:entreprise_update', args=[e.pk]), DONNEES)
        self.assertRedirects(r, reverse('entreprise:entreprise_list'))

    # ---- Supprimer
    def test_supprimer_page_confirmation_puis_post(self):
        e = Entreprise.objects.create(**DONNEES)
        url = reverse('entreprise:entreprise_delete', args=[e.pk])
        self.assertContains(self.client.get(url), 'Oui, supprimer')
        self.assertEqual(Entreprise.objects.count(), 1)   # un simple GET ne supprime rien
        self.assertRedirects(self.client.post(url), reverse('entreprise:entreprise_list'))
        self.assertEqual(Entreprise.objects.count(), 0)

    def test_supprimer_inexistant_404(self):
        self.assertEqual(self.client.post(reverse('entreprise:entreprise_delete', args=[999])).status_code, 404)

    # ---- Accès
    def test_visiteur_redirige_vers_connexion(self):
        self.client.logout()
        r = self.client.get(reverse('entreprise:entreprise_list'))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('utilisateur:login'), r.url)

    def test_client_non_admin_refuse(self):
        self.client.force_login(self.client_user)
        e = Entreprise.objects.create(**DONNEES)
        for nom, args in [('entreprise_list', []), ('entreprise_create', []), ('entreprise_detail', [e.pk]),
                          ('entreprise_update', [e.pk]), ('entreprise_delete', [e.pk])]:
            self.assertEqual(self.client.get(reverse(f'entreprise:{nom}', args=args)).status_code, 403, nom)
        self.assertEqual(self.client.post(reverse('entreprise:entreprise_delete', args=[e.pk])).status_code, 403)
        self.assertEqual(Entreprise.objects.count(), 1)

    # ---- Menu
    def test_lien_menu_admin_seulement(self):
        lien = 'href="%s"' % reverse('entreprise:entreprise_list')
        self.assertContains(self.client.get(reverse('utilisateur:dashboard')), lien)
        self.client.force_login(self.client_user)
        self.assertNotContains(self.client.get(reverse('utilisateur:dashboard')), lien)