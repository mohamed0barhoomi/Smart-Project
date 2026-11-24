from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Estimation, Projet

MDP = "MotDePasse!123"


class EstimationTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_user("admin1", password=MDP, is_staff=True)
        self.client_simple = User.objects.create_user("u1", password=MDP)
        self.projet = Projet.objects.create(nom="Boutique", proprietaire=self.client_simple)
        self.estimation = Estimation.objects.create(
            projet=self.projet, resume="Une boutique en ligne", cout=Decimal("12500"), delai=Decimal("4"))
        Projet.objects.create(nom="Sans estimation", proprietaire=self.client_simple)

    def test_dashboard_reserve_aux_admins(self):
        self.assertRedirects(self.client.get(reverse("dashboard")), "/connexion/?next=/",
                             fetch_redirect_response=False)
        self.client.force_login(self.client_simple)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)

    def test_dashboard(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("dashboard"))
        self.assertContains(r, "Boutique")
        self.assertContains(r, "12 500,00 DT")
        self.assertContains(r, "1 sans estimation")
        self.assertEqual(r.context["delai_moyen"], Decimal("4"))

    def test_modifier(self):
        self.client.force_login(self.admin)
        url = reverse("modifier_estimation", args=[self.projet.pk])
        r = self.client.post(url, {"resume": "Nouveau", "cout": "9000", "delai": "3.5", "hypotheses": ""})
        self.assertRedirects(r, reverse("dashboard"))
        self.estimation.refresh_from_db()
        self.assertEqual((self.estimation.cout, self.estimation.delai), (Decimal("9000"), Decimal("3.5")))

    def test_modifier_refuse_negatif(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("modifier_estimation", args=[self.projet.pk]),
                             {"resume": "", "cout": "-1", "delai": "2"})
        self.assertContains(r, "Le coût ne peut pas être négatif.")

    def test_supprimer(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("supprimer_estimation", args=[self.projet.pk]))
        self.assertRedirects(r, reverse("dashboard"))
        self.assertFalse(Estimation.objects.exists())
        self.assertTrue(Projet.objects.filter(pk=self.projet.pk).exists())   # le projet reste
