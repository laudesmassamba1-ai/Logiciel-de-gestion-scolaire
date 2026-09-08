"""Tests des sous-modules avances de l'assistante Charo :
langue (correction), maths (calculatrice AST), graphe (BFS),
contexte (anaphores) et leur integration dans AssistantIA.
"""

import pytest

from services.ia import langue, maths
from services.ia.contexte import ContexteConversation


# ----------------------------------------------------------------------
# langue.py
# ----------------------------------------------------------------------

class TestLangue:

    def test_damerau_base(self):
        assert langue.damerau("eleve", "eleve") == 0
        assert langue.damerau("elevs", "eleves") == 1
        assert langue.damerau("elvee", "eleve") == 1  # transposition
        assert langue.damerau("abc", "xyz") == 3

    def test_damerau_plafond_rapide(self):
        assert langue.damerau("abcdefghij", "x", plafond=2) == 3

    def test_correction_mot_connu_intact(self):
        vocab = {"moyenne", "caisse"}
        assert langue.corriger_phrase("solde de la caisse", vocab) == \
            "solde de la caisse"

    def test_correction_faute_de_frappe(self):
        vocab = {"eleves", "moyenne", "combien"}
        corrige = langue.corriger_phrase("combien d eleves", vocab)
        assert "eleve" in corrige

    def test_mots_courts_jamais_corriges(self):
        vocab = {"de", "la"}
        assert langue.corriger_phrase("de la", vocab) == "de la"

    def test_distance_2_exige_meme_prefixe(self):
        # « scolaire » ne doit pas devenir « salaire » (prefixes differents)
        vocab = {"salaire", "ecole"}
        resultat = langue.corriger_phrase("le scolaire", vocab)
        assert "scolaire" in resultat

    def test_similarite_dice(self):
        assert langue.similarite("Mambou Junior", "mambou junior") > 0.9
        assert langue.similarite("eleve", "tracteur") < 0.4


# ----------------------------------------------------------------------
# maths.py — calculatrice sure (AST, liste blanche)
# ----------------------------------------------------------------------

class TestMaths:

    def test_arithmetique_simple(self):
        assert maths.calculer("125000 - 45000")["valeur"] == 80000

    def test_avec_prefixe_calcule(self):
        assert maths.calculer("calcule 12+8")["valeur"] == 20

    def test_multiplication_x(self):
        assert maths.calculer("12 x 35")["valeur"] == 420

    def test_pourcentage(self):
        assert maths.calculer("20% de 500000")["valeur"] == 100000

    def test_racine_carree(self):
        assert maths.calculer("racine carree de 144")["valeur"] == 12

    def test_puissance_mot(self):
        assert maths.calculer("2 puissance 10")["valeur"] == 1024

    def test_separateur_milliers(self):
        assert maths.calculer("125 000 + 250 000")["valeur"] == 375000

    def test_statistiques_listes(self):
        assert maths.calculer("moyenne de 12 14 16")["valeur"] == 14
        assert maths.calculer("mediane de 8, 15, 9")["valeur"] == 9
        assert maths.calculer("ecart type de 10 12 14")["valeur"] == 2

    def test_division_par_zero_signalee(self):
        res = maths.calculer("5/0")
        assert res is not None and res["division_par_zero"]

    def test_injection_refusee(self):
        for mauvais in ("__import__('os')", "open('x')",
                        "().__class__.__bases__", "exec('x')"):
            assert maths.calculer(mauvais) is None

    def test_texte_ordinaire_refuse(self):
        assert maths.calculer("bonjour comment allez vous") is None
        assert maths.calculer("solde de la caisse") is None

    def test_nombre_seul_refuse(self):
        assert maths.calculer("125000") is None

    def test_puissance_geante_bloquee(self):
        res = maths.calculer("9**9**9")
        assert res is not None and res.get("erreur")

    def test_negatifs_et_priorites(self):
        assert maths.calculer("(12+8)x3 / 5")["valeur"] == 12
        assert maths.calculer("-5 + 10")["valeur"] == 5


# ----------------------------------------------------------------------
# contexte.py — anaphores
# ----------------------------------------------------------------------

class TestContexte:

    def test_suivi_classe(self):
        ctx = ContexteConversation()
        ctx.noter("combien d eleves en 6eme")
        assert ctx.reformuler("et en cm2 ?") == "combien d eleves en cm2"

    def test_suivi_classe_sans_classe_precedente(self):
        ctx = ContexteConversation()
        ctx.noter("combien d eleves")
        reformulee = ctx.reformuler("et en 5eme ?")
        assert "5eme" in reformulee and "combien" in reformulee

    def test_suivi_genre(self):
        ctx = ContexteConversation()
        ctx.noter("combien d eleves en 6eme")
        assert ctx.reformuler("et les filles ?") == \
            "combien de filles en 6eme"

    def test_suivi_eleve(self):
        ctx = ContexteConversation()
        ctx.noter("moyenne de mambou", eleve="Mambou Junior")
        assert ctx.reformuler("et ses paiements ?") == \
            "combien a paye Mambou Junior"

    def test_sans_historique_aucune_reformulation(self):
        ctx = ContexteConversation()
        assert ctx.reformuler("et en cm2 ?") is None

    def test_question_normale_non_touchee(self):
        ctx = ContexteConversation()
        ctx.noter("combien d eleves en 6eme")
        assert ctx.reformuler("solde de la caisse") is None

    def test_fenetre_glissante(self):
        ctx = ContexteConversation()
        for i in range(15):
            ctx.noter(f"question {i}")
        assert len(ctx.historique) <= 10


# ----------------------------------------------------------------------
# Integration moteur
# ----------------------------------------------------------------------

@pytest.fixture
def base_vierge(monkeypatch, tmp_path):
    import sys
    data = tmp_path / "data"
    data.mkdir(parents=True)
    monkeypatch.setenv("GS_DATA_DIR", str(data))
    import database.db
    db_module = sys.modules["database.db"]
    monkeypatch.setattr(db_module, "DB_PATH", data / "ecole.db")
    monkeypatch.setattr(db_module, "DOCS_DIR", data / "documents")
    from database import db
    db._initialized = False
    db.init_db()
    yield db
    db._initialized = False


def _assistant():
    from services.assistant_ia import AssistantIA
    return AssistantIA({"username": "dir", "nom_complet": "Directeur Test",
                        "prenom": "Paul", "role": "directeur"})


class TestIntegrationAvancee:

    def test_calcul_via_moteur(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("calcule 20% de 500000")
        assert "100000" in rep["texte"]

    def test_structure_ecole(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("structure de lecole")
        assert "relations" in rep["texte"]

    def test_lien_introuvable_message_propre(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("lien entre zzzz et yyyy")
        assert "trouve pas" in rep["texte"]

    def test_anaphore_complete_via_moteur(self, base_vierge):
        ia = _assistant()
        ia.traiter("combien d eleves ?")
        rep = ia.traiter("et en cm2 ?")
        assert "CM2" in rep["texte"] or "cm2" in rep["texte"]

    def test_reinitialiser_oublie_le_fil(self, base_vierge):
        ia = _assistant()
        ia.traiter("combien d eleves ?")
        ia.reinitialiser()
        assert ia.contexte.historique == []

    def test_graphe_chemin_apres_insertion(self, base_vierge):
        ia = _assistant()
        from database import db
        conn = db.connect()
        conn.execute(
            "INSERT INTO cycles (nom) VALUES ('GrapheTestCycle')")
        cid = conn.execute(
            "SELECT id FROM cycles WHERE nom='GrapheTestCycle'"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO classes (nom, cycle_id) "
            "VALUES ('GrapheTestClass', ?)", (cid,))
        clid = conn.execute(
            "SELECT id FROM classes WHERE nom='GrapheTestClass'"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO eleves (uuid_client, matricule, nom, "
            "prenom, sexe, classe_id) VALUES "
            "('u2', 'GM999', 'GrapheTestNom', 'GraphePrenom', 'M', ?)",
            (clid,))
        conn.commit()
        ia._graphe.construire(force=True)
        rep = ia.traiter("lien entre GraphePrenom et GrapheTestCycle")
        assert "Lien le plus court" in rep["texte"]
        assert "grapheprenom" in rep["texte"].lower()
