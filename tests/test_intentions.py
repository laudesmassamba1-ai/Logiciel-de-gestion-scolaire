"""Tests du routeur d'intentions de Charo (phase P1, projet v2).

Le routeur doit etre : deterministe, explicable, insensible a la casse et
aux accents, et surtout SANS REGRESSION — un handler choisi a tort renvoie
None et l'appelant rebascule sur l'ancien ordre fixe.
"""

import sys

import pytest

sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.parent)


class TestBareme:
    def test_aucun_mot_aucun_score(self):
        from services.ia.intentions import Intention
        i = Intention(nom="t", cles=("moyenne",), handler="_q_moyennes")
        assert i.scorer("bonjour") == 0.0

    def test_cle_unique_au_dessus_du_seuil(self):
        from services.ia.intentions import Intention
        i = Intention(nom="t", cles=("moyenne",), mots=("note", "bulletin"),
                      handler="_q_moyennes")
        assert i.scorer("quelle moyenne ?") == pytest.approx(0.60)

    def test_deux_cles_donnent_la_confiance(self):
        from services.ia.intentions import Intention
        i = Intention(nom="t", cles=("classement", "rang"), handler="_q_classement")
        assert i.scorer("classement et rang") >= 0.80

    def test_mot_unique_d_appoint_reste_sous_le_seuil(self):
        from services.ia.intentions import Intention
        i = Intention(nom="t", mots=("moyenne", "note"), poids=1.0,
                      handler="_q_moyennes")
        assert i.scorer("moyenne ?") == pytest.approx(0.30)
        assert i.scorer("moyenne et note ?") >= 0.45

    def test_poids_amplifie_et_plafonne(self):
        from services.ia.intentions import Intention
        faible = Intention(nom="f", cles=("caisse",), poids=0.5, handler="h")
        fort = Intention(nom="F", cles=("caisse",), poids=1.2, handler="h")
        assert fort.scorer("caisse") > faible.scorer("caisse")
        assert fort.scorer("caisse") <= 1.0

    def test_mot_entier_pas_prefixe(self):
        from services.ia.intentions import Intention
        i = Intention(nom="t", cles=("moyenne",), handler="_q_moyennes")
        assert i.scorer("moyenneponderee") == 0.0

    def test_regex_bonifie_une_intention(self):
        from services.ia.intentions import Intention
        avec = Intention(nom="t", mots=("caisse",),
                         expressions=(r"etat de la caisse",), handler="h")
        sans = Intention(nom="t", mots=("caisse",), handler="h")
        assert avec.scorer("etat de la caisse") > sans.scorer("etat de la caisse")

    def test_casse_et_accents_indifferents(self):
        from services.ia.intentions import Intention
        i = Intention(nom="t", cles=("eleve",), handler="h")
        assert i.scorer("Élève") == i.scorer("eleve") == i.scorer("ELEVE")

    def test_sans_mot_mais_regex(self):
        from services.ia.intentions import Intention
        i = Intention(nom="t", expressions=(r"combien d['’]? ?eleves",),
                      handler="_q_effectifs")
        assert i.scorer("combien d'eleves en 6eB ?") > 0.0


class TestResolution:
    CAS = [
        ("Quelle est la moyenne generale de Mbemba ?", "moyenne_generale"),
        ("Quel est le classement de la classe 6eB ?", "classement"),
        ("Est-ce que Mbemba a paye sa scolarite ?", "paiements_eleve"),
        ("Quels sont les frais de la classe ?", "tarifs_classe"),
        ("Quel est l'etat de la caisse ?", "caisse"),
        ("Qui est le professeur de 6eB ?", "personnel"),
        ("Quel trimestre sommes-nous ?", "annee_active"),
        ("Combien d'eleves en 6eB ?", "effectifs"),
        ("Combien d'absences a Mbemba ?", "absences"),
        ("Affiche la fiche de Mbemba", "fiche_eleve"),
        ("Quels sont les liens entre Mbemba et 6eB ?", "graphe"),
    ]

    @pytest.mark.parametrize("question,intention_attendue", CAS)
    def test_question_type_resout(self, question, intention_attendue):
        from services.ia.intentions import get_routeur
        b, score, _c = get_routeur().resoudre(question)
        assert b is not None, get_routeur().expliquer(question)
        assert b.nom == intention_attendue, get_routeur().expliquer(question)
        assert score >= 0.45

    @pytest.mark.parametrize("question,intention_attendue", CAS)
    def test_marge_sur_la_deuxieme(self, question, intention_attendue):
        """Une intention retenue doit dominer la suivante, sinon la question
        est ambiguë et il vaut mieux laisser le parcours historique."""
        from services.ia.intentions import get_routeur
        b, score, classement = get_routeur().resoudre(question)
        autres = [s for i, s in classement if i.nom != intention_attendue]
        if autres:
            assert score - max(autres) >= 0.05, get_routeur().expliquer(question)

    def test_deux_cles_declenchent_le_court_circuit(self):
        from services.ia.intentions import get_routeur
        for q in ("Quel est le classement et le rang de la classe ?",
                  "Moyenne generale et rang de Jean ?"):
            _b, score, _c = get_routeur().resoudre(q)
            assert score >= 0.80, f"{q} : {score:.2f}"

    def test_hors_perimetre_aucune_intention(self):
        from services.ia.intentions import get_routeur
        for hors in ("bonjour", "merci beaucoup", "au revoir", "comment vas-tu ?"):
            b, score, _c = get_routeur().resoudre(hors)
            assert b is None, f"{hors} -> {b.nom if b else None}"
            assert score == 0.0

    def test_seuil_personnalise_rejette(self):
        from services.ia.intentions import get_routeur
        _b, score, _c = get_routeur().resoudre("Combien d'eleves en 6eB ?",
                                               seuil=0.99)
        assert score < 0.99

    def test_expliquer_liste_le_classement(self):
        from services.ia.intentions import get_routeur
        texte = get_routeur().expliquer("Quelle est sa moyenne generale ?")
        assert "moyenne_generale" in texte
        assert "handler _q_moyenne_generale" in texte

    def test_registre_coherent(self):
        """Chaque intention doit pointer vers un handler reellement declare
        (evite un handler fantome) et fournir un exemple."""
        from services.assistant_ia import HANDLERS_METIER
        from services.ia.intentions import get_routeur
        for intention in get_routeur().intentions:
            assert intention.handler in HANDLERS_METIER, intention.nom
            assert intention.exemple


class TestIntegriteRegistre:
    def test_les_douze_handlers_historiques_sont_declares(self):
        from services.assistant_ia import HANDLERS_METIER
        from services.ia.intentions import get_routeur
        declares = {i.handler for i in get_routeur().intentions}
        assert declares == set(HANDLERS_METIER)

    def test_noms_uniques(self):
        from services.ia.intentions import get_routeur
        noms = [i.nom for i in get_routeur().intentions]
        assert len(noms) == len(set(noms))

    def test_ordre_du_registre_tie_break(self):
        """A score egal, l'intention declaree en premier l'emporte."""
        from services.ia.intentions import RouteurIntentions, Intention
        a = Intention(nom="zzz_avant", cles=("x",), handler="_q_caisse")
        b = Intention(nom="aaa_apres", cles=("x",), handler="_q_caisse")
        r = RouteurIntentions((a, b))
        meilleure, _s, _c = r.resoudre("x")
        assert meilleure.nom == "zzz_avant"
