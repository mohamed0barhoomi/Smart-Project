from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from Chat_App.generateur import en_nombre, enregistrer_analyse, generer_analyse
from Chat_App.models import Message
from Projet_App.models import Projet
from UtilisateursApp.models import User

from .models import Estimation

MDP = "MotDePasse!123"


class EnNombreTests(TestCase):
    """Lecture tolérante des nombres renvoyés par l'IA."""

    def test_formats_acceptes(self):
        maxi = Decimal("1000000")
        self.assertEqual(en_nombre(12000, maxi), Decimal("12000"))
        self.assertEqual(en_nombre(4.5, maxi), Decimal("4.5"))
        self.assertEqual(en_nombre("12 000 DT", maxi), Decimal("12000"))
        self.assertEqual(en_nombre("4,5 mois", maxi), Decimal("4.5"))

    def test_valeurs_refusees(self):
        maxi = Decimal("1000")
        for valeur in [None, "", "beaucoup", True, [], -3, 5000]:
            self.assertIsNone(en_nombre(valeur, maxi), valeur)


class GenerationEstimationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("u1", "u1@gmail.com", MDP)
        self.projet = Projet.objects.create(nom="Boutique", proprietaire=self.user)

    def test_cree_puis_remplace(self):
        enregistrer_analyse(self.projet, {"estimation": {"resume": "R1", "cout": 1000, "delai_mois": 2}})
        enregistrer_analyse(self.projet, {"estimation": {"resume": ["R2", "suite"], "cout": "2 500,5", "delai_mois": "3"}})
        self.assertEqual(Estimation.objects.count(), 1)
        e = Estimation.objects.get()
        self.assertEqual(e.resume, "R2\nsuite")
        self.assertEqual(e.cout, Decimal("2500.50"))
        self.assertEqual(e.delai, Decimal("3.0"))

    def test_estimation_illisible_garde_l_ancienne(self):
        enregistrer_analyse(self.projet, {"estimation": {"cout": 1000, "delai_mois": 2}})
        _, ok = enregistrer_analyse(self.projet, {"estimation": {"cout": "?"}})
        self.assertFalse(ok)
        self.assertEqual(Estimation.objects.get().cout, Decimal("1000.00"))

    def test_generer_analyse_avertit_si_pas_d_estimation(self):
        Message.objects.create(projet=self.projet, role="user", contenu="Une boutique en ligne")
        with patch("Chat_App.generateur.appeler_llm", return_value=({}, "modele-test")):
            _, avertissement = generer_analyse(self.projet)
        self.assertIn("estimation n'a pas été mise à jour", avertissement)


class EstimationVuesTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("u1", "u1@gmail.com", MDP)
        self.autre = User.objects.create_user("u2", "u2@gmail.com", MDP)
        self.projet = Projet.objects.create(nom="Boutique", proprietaire=self.user)
        self.client.force_login(self.user)

    def url(self, nom):
        return reverse(nom, args=[self.projet.pk])

    def creer(self):
        return Estimation.objects.create(projet=self.projet, resume="Résumé", cout=Decimal("12500"), delai=Decimal("4"))

    def test_page_sans_estimation(self):
        r = self.client.get(self.url("estimation_detail"))
        self.assertContains(r, "Pas encore d'estimation")
        self.assertContains(r, 'class="nav-link active">Estimation</a>')
        self.assertEqual(self.client.get(self.url("estimation_update")).status_code, 404)
        self.assertEqual(self.client.get(self.url("estimation_delete")).status_code, 404)

    def test_affichage(self):
        self.creer()
        r = self.client.get(self.url("estimation_detail"))
        self.assertContains(r, "12 500,00 DT")
        self.assertContains(r, "4 mois")
        self.assertContains(self.client.get(reverse("projet_detail", args=[self.projet.pk])), "Coût estimé")

    def test_modifier(self):
        self.creer()
        r = self.client.post(self.url("estimation_update"),
                             {"resume": "Nouveau", "cout": "9000", "delai": "3.5", "hypotheses": ""})
        self.assertRedirects(r, self.url("estimation_detail"))
        e = Estimation.objects.get()
        self.assertEqual((e.resume, e.cout, e.delai), ("Nouveau", Decimal("9000"), Decimal("3.5")))

    def test_modifier_refuse_negatif(self):
        self.creer()
        r = self.client.post(self.url("estimation_update"), {"resume": "", "cout": "-1", "delai": "2"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Le coût ne peut pas être négatif.")

    def test_supprimer(self):
        self.creer()
        r = self.client.post(self.url("estimation_delete"))
        self.assertRedirects(r, self.url("estimation_detail"))
        self.assertFalse(Estimation.objects.exists())

    def test_pas_d_acces_au_projet_d_un_autre(self):
        self.creer()
        self.client.force_login(self.autre)
        for nom in ["estimation_detail", "estimation_update", "estimation_delete"]:
            self.assertEqual(self.client.get(self.url(nom)).status_code, 404, nom)


class TableauDeBordAdminTests(TestCase):

    def test_totaux_et_graphiques(self):
        admin = User.objects.create_user("admin1", "admin1@gmail.com", MDP, role="ADMIN")
        user = User.objects.create_user("u1", "u1@gmail.com", MDP)
        for nom, cout, delai in [("A", "1000", "2"), ("B", "3000", "4")]:
            p = Projet.objects.create(nom=nom, proprietaire=user)
            Estimation.objects.create(projet=p, cout=Decimal(cout), delai=Decimal(delai))
        self.client.force_login(admin)
        r = self.client.get(reverse("utilisateur:dashboard"))
        self.assertContains(r, "Estimations des projets")
        self.assertContains(r, "4 000,00")   # coût total
        self.assertContains(r, 'id="graphCout"')
        self.assertEqual(r.context["delai_moyen"], Decimal("3"))
