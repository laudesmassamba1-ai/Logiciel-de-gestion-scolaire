import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def base_vierge(tmp_path, monkeypatch):
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


DIRECTEUR = {"id": 1, "role": "directeur", "nom_complet": "Jean Directeur",
             "username": "dir"}


def _moteur():
    from services.ia.apprentissage import MoteurApprentissage
    return MoteurApprentissage()


def _assistant(user=DIRECTEUR):
    from services.assistant_ia import AssistantIA
    return AssistantIA(user)


class TestJournal:
    def test_consigner_trace_un_tour(self, base_vierge):
        m = _moteur()
        m.consigner("combien d eleves", "Il y a 12 eleves.", "corpus")
        ligne = base_vierge.query_one(
            "SELECT * FROM ia_journal ORDER BY id DESC LIMIT 1")
        assert ligne["question"] == "combien d eleves"
        assert ligne["source"] == "corpus"

    def test_consigner_ignore_vide(self, base_vierge):
        m = _moteur()
        m.consigner("", "rien", "moteur")
        m.consigner(None, "rien", "moteur")
        c = base_vierge.query_one("SELECT COUNT(*) AS c FROM ia_journal")
        assert c["c"] == 0

    def test_journal_purge_a_la_limite(self, base_vierge):
        m = _moteur()
        for i in range(1510):
            m.consigner(f"question {i}", f"reponse {i}", "moteur")
        c = base_vierge.query_one("SELECT COUNT(*) AS c FROM ia_journal")
        assert c["c"] == 1500
        ancien = base_vierge.query_one(
            "SELECT COUNT(*) AS c FROM ia_journal WHERE question = "
            "'question 0'")
        assert ancien["c"] == 0
        recent = base_vierge.query_one(
            "SELECT COUNT(*) AS c FROM ia_journal WHERE question = "
            "'question 1509'")
        assert recent["c"] == 1


class TestMemoireSchema:
    def test_migration_ajoute_colonnes(self, base_vierge):
        # db.init_db() cree deja ia_memoire au schema historique (sans les
        # colonnes d'apprentissage). ensure_tables() doit le migrer.
        _moteur().ensure_tables()
        colonnes = {r["name"]
                    for r in base_vierge.query("PRAGMA table_info(ia_memoire)")}
        assert {"score", "source", "dernier_usage"} <= colonnes

    def test_tables_creees(self, base_vierge):
        _moteur().ensure_tables()
        for table in ("ia_memoire", "ia_feedback", "ia_journal",
                      "ia_metriques"):
            ligne = base_vierge.query_one(
                "SELECT COUNT(*) AS c FROM sqlite_master "
                "WHERE type = 'table' AND name = ?", (table,))
            assert ligne["c"] == 1


class TestFeedback:
    def test_noter_positif_renforce(self, base_vierge):
        from services.assistant_ia import AssistantIA
        ia = AssistantIA(DIRECTEUR)
        ia.traiter("retiens que le coatch de foot est monsieur Loembe")
        ia.traiter("qui est le coatch de foot ?")
        av = base_vierge.query_one("SELECT score FROM ia_memoire")
        ia.noter_reponse(1)
        av2 = base_vierge.query_one("SELECT score FROM ia_memoire")
        assert av2["score"] > av["score"]
        fb = base_vierge.query_one("SELECT note FROM ia_feedback")
        assert fb["note"] == 1

    def test_noter_negatif_degrade(self, base_vierge):
        from services.assistant_ia import AssistantIA
        ia = AssistantIA(DIRECTEUR)
        ia.traiter("quand je dis coatch tu dis monsieur Ibara")
        ia.traiter("qui est le coatch de foot ?")
        score_avant = base_vierge.query_one(
            "SELECT score FROM ia_memoire WHERE question = 'coatch'")
        ia.noter_reponse(-1, motif="mauvaise reponse")
        score_apres = base_vierge.query_one(
            "SELECT score FROM ia_memoire WHERE question = 'coatch'")
        assert score_apres["score"] < score_avant["score"]
        fb = base_vierge.query_one("SELECT note, motif FROM ia_feedback")
        assert fb["note"] == -1
        assert fb["motif"] == "mauvaise reponse"

    def test_noter_zero_ignore(self, base_vierge):
        m = _moteur()
        m.noter("q", "r", 0)
        c = base_vierge.query_one("SELECT COUNT(*) AS c FROM ia_feedback")
        assert c["c"] == 0

    def test_rejeu_renforce(self, base_vierge):
        m = _moteur()
        m.ensure_tables()
        base_vierge.execute(
            "INSERT INTO ia_memoire (question, reponse, usage) "
            "VALUES (?, ?, 3)", ("qui est absent", "personne"))
        m.vu_memoire(1)
        ligne = base_vierge.query_one("SELECT usage, score, dernier_usage "
                                      "FROM ia_memoire WHERE id = 1")
        assert ligne["usage"] == 4
        assert ligne["score"] > 1.0
        assert ligne["dernier_usage"]


class TestAutoAmelioration:
    def test_fusion_doublons(self, base_vierge):
        m = _moteur()
        m.ensure_tables()
        for question in ("quelle est la moyenne de antoine",
                         "quelle est la moyenne de antoine",
                         "quelle est la moyenne de antoine "):
            base_vierge.execute(
                "INSERT INTO ia_memoire (question, reponse) VALUES (?, ?)",
                (question, "antonio a 12"))
        base_vierge.execute("UPDATE ia_memoire SET usage = 2 WHERE id = 1")
        rapport = m.ameliorer(force=True)
        assert rapport["fusionne"] >= 1
        assert m.statistiques()["apprentissages"] <= 2

    def test_ne_fusionne_pas_differents(self, base_vierge):
        m = _moteur()
        m.ensure_tables()
        for question in ("quelle est la moyenne de antoine",
                         "combien a paye marie"):
            base_vierge.execute(
                "INSERT INTO ia_memoire (question, reponse) VALUES (?, ?)",
                (question, "x"))
        rapport = m.ameliorer(force=True)
        assert rapport["fusionne"] == 0
        assert m.statistiques()["apprentissages"] == 2

    def test_supprime_apprentissages_faibles(self, base_vierge):
        m = _moteur()
        m.ensure_tables()
        base_vierge.execute(
            "INSERT INTO ia_memoire (question, reponse, usage, score) "
            "VALUES (?, ?, 0, 0.1)", ("mauvais souvenir", "bzzt"))
        base_vierge.execute(
            "INSERT INTO ia_memoire (question, reponse, usage, score) "
            "VALUES (?, ?, 5, 1.0)", ("bon souvenir", "ok"))
        rapport = m.ameliorer(force=True)
        assert rapport["retires"] == 1
        reste = base_vierge.query_one(
            "SELECT COUNT(*) AS c FROM ia_memoire WHERE question = "
            "'bon souvenir'")
        assert reste["c"] == 1

    def test_cooldown_bloque_repetition(self, base_vierge):
        m = _moteur()
        m.ameliorer(force=True)
        rapport = m.ameliorer()
        assert rapport["publicite"] is False


class TestIntegration:
    def test_memoire_rejouee_et_journalisee(self, base_vierge):
        ia = _assistant()
        ia.traiter("retiens que le coatch de foot est monsieur Loembe")
        rep = ia.traiter("qui est le coatch de foot ?")
        assert "Loembe" in rep["texte"]
        assert "retenu" in rep["texte"] or "appris" in rep["texte"]
        ligne = base_vierge.query_one(
            "SELECT source FROM ia_journal ORDER BY id DESC LIMIT 1")
        assert ligne["source"] == "memoire"
        usa = base_vierge.query_one("SELECT usage FROM ia_memoire")
        assert usa["usage"] == 1

    def test_stats_via_phrase(self, base_vierge):
        ia = _assistant()
        ia.traiter("retiens que le coatch de foot est monsieur Loembe")
        rep = ia.traiter("montre tes statistiques")
        assert "souvenir" in rep["texte"]
        assert "question" in rep["texte"]

    def test_ameliore_toi_via_phrase(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("ameliore-toi")
        assert "Amelioration terminee" in rep["texte"]

    def test_apprend_automatiquement_reponse_llm(self, base_vierge):
        ia = _assistant()
        ia.traiter("retiens que tu reponds par toutou quand on dit kikou")
        ia.traiter("kikou")
        ia._last_llm_reponse = "toutou !"
        rep = ia.traiter("apprendre cette reponse")
        assert "retenu" in rep["texte"]
        rep2 = ia.traiter("kikou")
        assert "toutou" in rep2["texte"]

    def test_feedback_public_retourne_texte(self, base_vierge):
        ia = _assistant()
        ia.traiter("bonjour")
        rep = ia.noter_reponse(1)
        assert isinstance(rep, dict) and rep["texte"]
        neg = ia.noter_reponse(-1)
        assert "m'améliorer" in neg["texte"]

    def test_statistiques_publiques(self, base_vierge):
        ia = _assistant()
        stats = ia.statistiques()
        assert "apprentissages" in stats
        assert "rejeux" in stats
        assert "feedback_pos" in stats


GESTIONNAIRE = {"id": 2, "role": "gestionnaire",
                "nom_complet": "Marie Gestion", "username": "marie"}


class TestMemoireParUtilisateur:
    def test_colonne_utilisateur_id_inscrite(self, base_vierge):
        _assistant().traiter("retiens que le portail ferme a 19h")
        ligne = base_vierge.query_one(
            "SELECT utilisateur_id FROM ia_memoire ORDER BY id DESC LIMIT 1")
        assert ligne["utilisateur_id"] == DIRECTEUR["id"]

    def test_migration_ajoute_la_colonne(self, base_vierge):
        _moteur().ensure_tables()          # ajoute la colonne si absente
        base_vierge.execute(
            "ALTER TABLE ia_memoire DROP COLUMN utilisateur_id")
        _moteur().ensure_tables()
        colonnes = {r["name"] for r in
                    base_vierge.query("PRAGMA table_info(ia_memoire)")}
        assert "utilisateur_id" in colonnes

    def test_a_ne_voit_pas_la_memoire_de_b(self, base_vierge):
        ia_a = _assistant(DIRECTEUR)
        ia_b = _assistant(GESTIONNAIRE)
        ia_a.traiter("retiens que le mot de passe wifi est cactus")
        rep = ia_b.traiter("mot de passe wifi ?")
        assert "cactus" not in rep["texte"]
        rep = ia_a.traiter("mot de passe wifi ?")
        assert "cactus" in rep["texte"]

    def test_oublie_vise_la_memoire_de_son_utilisateur(self, base_vierge):
        ia_a = _assistant(DIRECTEUR)
        ia_b = _assistant(GESTIONNAIRE)
        ia_a.traiter("retiens que la salle des profs est au rez de chaussee")
        ia_b.traiter("retiens que la salle des profs est au premier etage")
        ia_b.traiter("oublie la salle des profs")
        reste = base_vierge.query_one(
            "SELECT COUNT(*) AS c FROM ia_memoire "
            "WHERE utilisateur_id = ?", (DIRECTEUR["id"],))
        assert reste["c"] == 1


class TestApprentissageRapide:
    def test_retient_qualite_pour_l_eleve(self, base_vierge):
        from services.assistant_ia import apprentissage_rapide
        question = apprentissage_rapide(DIRECTEUR, "Lea", "Mbang", "bon en maths")
        assert question and "Lea" in question
        ligne = base_vierge.query_one(
            "SELECT * FROM ia_memoire WHERE question = ?", (question,))
        assert ligne is not None
        assert ligne["source"] == "fiche"
        assert ligne["utilisateur_id"] == DIRECTEUR["id"]

    def test_idempotent(self, base_vierge):
        from services.assistant_ia import apprentissage_rapide
        premier = apprentissage_rapide(DIRECTEUR, "Lea", "Mbang", "bon en maths")
        second = apprentissage_rapide(DIRECTEUR, "Lea", "Mbang", "bon en maths")
        assert premier is not None and second is None
        c = base_vierge.query_one(
            "SELECT COUNT(*) AS c FROM ia_memoire WHERE question = ?",
            (premier,))
        assert c["c"] == 1

    def test_prenom_vide_ignore(self, base_vierge):
        from services.assistant_ia import apprentissage_rapide
        assert apprentissage_rapide(DIRECTEUR, "", "", "bon en maths") is None

    def test_rejoue_depuis_le_chat_du_meme_utilisateur(self, base_vierge):
        from services.assistant_ia import apprentissage_rapide
        apprentissage_rapide(DIRECTEUR, "Lea", "Mbang", "bon en maths")
        rep = _assistant(DIRECTEUR).traiter("lea mbang est comment en maths ?")
        assert "bon en maths" in rep["texte"]


class TestExportMemoire:
    def test_export_csv_filtré_par_utilisateur(self, base_vierge, tmp_path):
        from pathlib import Path
        from services.assistant_ia import exporter_memoire
        ia_a = _assistant(DIRECTEUR)
        ia_b = _assistant(GESTIONNAIRE)
        ia_a.traiter("retiens que la cantine ouvre a midi")
        ia_b.traiter("retiens que la cantine ouvre a 13h")
        chemin = Path(exporter_memoire(tmp_path / "mem.csv",
                                       utilisateur=DIRECTEUR))
        lignes = chemin.read_text(encoding="utf-8-sig").strip().splitlines()
        assert lignes[0].startswith("id,type,question,reponse")
        assert len(lignes) == 2   # en-tete + 1 ligne propre a l'utilisateur
        assert "midi" in lignes[1]

    def test_export_vide_cree_un_fichier(self, base_vierge, tmp_path):
        from pathlib import Path
        from services.assistant_ia import exporter_memoire
        chemin = Path(exporter_memoire(tmp_path / "mem.csv",
                                       utilisateur=DIRECTEUR))
        assert chemin.exists()
        assert len(chemin.read_text(encoding="utf-8-sig").strip().splitlines()) == 1