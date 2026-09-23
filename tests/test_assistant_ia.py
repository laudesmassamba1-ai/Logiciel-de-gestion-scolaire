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
GESTIONNAIRE = {"id": 2, "role": "gestionnaire", "nom_complet": "Gest Test",
                "username": "gest"}


def _assistant(user=DIRECTEUR):
    from services.assistant_ia import AssistantIA
    return AssistantIA(user)


CLASSES_NOMS = ("P1", "CP1", "CE1", "CM2", "6eme")


def _classe_id(db, nom):
    ligne = db.query_one("SELECT id FROM classes WHERE nom = ?", (nom,))
    return ligne["id"] if ligne else None


def _ajouter_eleve(db, nom, prenom, classe_nom, sexe="M"):
    return db.execute(
        """INSERT INTO eleves (uuid_client, matricule, nom, prenom, sexe,
           date_naissance, lieu_naissance, classe_id, statut)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Inscrit')""",
        (f"u-{nom}-{prenom}", f"M{nom[:3]}{prenom[:3]}", nom, prenom, sexe,
         "2010-05-14", "Brazzaville", _classe_id(db, classe_nom)))


class TestUtilitaires:
    def test_normaliser_accents_et_apostrophes(self):
        from services.assistant_ia import normaliser
        assert normaliser("Combien d'élèves en 6ème ?") == \
            "combien d eleves en 6eme"
        assert normaliser("  ÉCOLE   à  côté ") == "ecole a cote"

    def test_formater_fcfa(self):
        from services.assistant_ia import formater_fcfa
        assert formater_fcfa(5000) == "5 000 FCFA"
        assert formater_fcfa(1250000.5) == "1 250 000.50 FCFA"

    def test_appreciation(self, base_vierge):
        from services.assistant_ia import appreciation
        assert appreciation(17) == "Excellent"
        assert appreciation(10) == "Assez bien"
        assert appreciation(7.9) == "Insuffisant"

    def test_formater_date_invalide(self):
        from services.assistant_ia import formater_date
        assert formater_date("pas une date") == "pas une date"


class TestIndexSemantique:
    def test_retrouve_le_bon_document(self):
        from services.assistant_ia import IndexSemantique
        idx = IndexSemantique()
        idx.ajouter("La reunion des parents est le samedi matin.")
        idx.ajouter("Le logo de l'ecole se change dans parametres.")
        idx.construire()
        res = idx.rechercher("quand a lieu la reunion des parents ?")
        assert res is not None
        score, texte = res
        assert "samedi" in texte

    def test_aucun_document_pertinent(self):
        from services.assistant_ia import IndexSemantique
        idx = IndexSemantique()
        idx.ajouter("La reunion des parents est le samedi matin.")
        idx.construire()
        assert idx.rechercher("blorg xzyy wtfzz") is None


class TestCalculLibre:
    def test_addition_soustraction(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("calcule 125000 - 45000")
        assert "80000" in rep["texte"]

    def test_multiplication_avec_x(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("12 x 35")
        assert "420" in rep["texte"]

    def test_division_par_zero(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("5/0")
        assert "zero" in rep["texte"].lower()

    def test_puissance_refusee(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("9**9**9")
        assert rep["action"] is None
        assert "=" not in rep["texte"]

    def test_texte_ordinaire_non_calcul(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("solde de la caisse")
        assert "Caisse" in rep["texte"] or "caisse" in rep["texte"].lower()


class TestSalutationsEtAide:
    def test_bonjour(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("bonjour")
        # Check for greeting (may or may not include "Charo" depending on random choice)
        texte = rep["texte"].lower()
        assert "bonjour" in texte or "salut" in texte or "coucou" in texte or "charo" in texte

    def test_aide_liste_capacites(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("aide")
        # Check for key capabilities in the personality-wrapped response
        texte = rep["texte"].lower()
        assert "renseigner" in texte or "combien d'élèves" in texte
        assert "apprendre" in texte or "retiens que" in texte

    def test_manuel_comment_sauvegarder(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("comment sauvegarder la base ?")
        assert "sauvegarde" in rep["texte"].lower()

    def test_entree_vide(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("")
        # Empty input triggers aide
        assert "charlie" not in rep["texte"].lower()  # Just ensure it responds
        assert len(rep["texte"]) > 10  # Should have substantial response


class TestEffectifs:
    def test_total_zero_eleve(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("combien d'eleves ?")
        texte = rep["texte"].lower()
        assert "0" in texte and "élève" in texte or "eleve" in texte

    def test_total_par_sexe(self, base_vierge):
        db = base_vierge
        _ajouter_eleve(db, "Mambou", "Junior", "6eme", "M")
        _ajouter_eleve(db, "Ngo", "Marie", "6eme", "F")
        _ajouter_eleve(db, "Bala", "Paul", "CM2", "M")
        ia = _assistant()
        rep = ia.traiter("combien de filles ?")
        texte = rep["texte"].lower()
        assert "1" in texte and "fille" in texte
        assert "2" not in texte or "fille" not in texte or "2 fille" not in texte
        rep = ia.traiter("combien d'eleves en tout ?")
        texte = rep["texte"].lower()
        assert "3" in texte and ("élève" in texte or "eleve" in texte)
        assert "1" in texte and "fille" in texte
        assert "2" in texte and "garçon" in texte

    def test_effectif_dune_classe(self, base_vierge):
        db = base_vierge
        _ajouter_eleve(db, "Mambou", "Junior", "6eme")
        _ajouter_eleve(db, "Ngo", "Marie", "6eme", "F")
        ia = _assistant()
        rep = ia.traiter("combien d'eleves en 6eme ?")
        texte = rep["texte"].lower()
        assert "6eme" in texte or "6ème" in texte
        assert "2" in texte and ("élève" in texte or "eleve" in texte)


class TestMoyennes:
    def _preparer_notes(self, db):
        db.execute("INSERT OR IGNORE INTO matieres (nom, coefficient) "
                   "VALUES ('Maths', 1)")
        m1 = db.query_one("SELECT id FROM matieres WHERE nom = 'Maths'")["id"]
        m2 = db.execute(
            "UPDATE matieres SET coefficient = 3 WHERE nom = 'Francais'")
        m2 = db.query_one("SELECT id FROM matieres WHERE nom = 'Francais'")["id"]
        e1 = _ajouter_eleve(db, "Mambou", "Junior", "6eme")
        e2 = _ajouter_eleve(db, "Ngo", "Marie", "6eme", "F")
        for eid in (e1, e2):
            db.execute(
                """INSERT INTO notes (eleve_id, matiere_id, periode,
                   devoir1, devoir2, composition) VALUES (?, ?, ?, ?, ?, ?)""",
                (eid, m1, "1er Trimestre", 10, 12, 14))
            db.execute(
                """INSERT INTO notes (eleve_id, matiere_id, periode,
                   devoir1, devoir2, composition) VALUES (?, ?, ?, ?, ?, ?)""",
                (eid, m2, "1er Trimestre", 16, 16, 16))
        return e1, e2

    def test_moyenne_eleve_formule_officielle(self, base_vierge):
        db = base_vierge
        self._preparer_notes(db)
        ia = _assistant()
        rep = ia.traiter("quelle est la moyenne de Mambou Junior ?")
        # Maths : (10+12+2*14)/4 = 12.5 ; Francais : 16
        # Generale : (12.5*1 + 16*3)/4 = 15.125 -> 15.12 (arrondi Python)
        assert "15.12" in rep["texte"]
        assert "Tres bien" in rep["texte"] or "Très bien" in rep["texte"]

    def test_moyenne_par_periode_vide(self, base_vierge):
        db = base_vierge
        self._preparer_notes(db)
        ia = _assistant()
        rep = ia.traiter("moyenne de Mambou au 2eme trimestre")
        assert "Aucune note" in rep["texte"]

    def test_classement_classe_et_moyenne_generale(self, base_vierge):
        db = base_vierge
        self._preparer_notes(db)
        ia = _assistant()
        rep = ia.traiter("moyenne de la classe 6eme")
        assert "6eme" in rep["texte"] or "6ème" in rep["texte"]
        assert "2" in rep["texte"] and ("élève" in rep["texte"] or "eleve" in rep["texte"])
        assert "15.12" in rep["texte"]

    def test_egalite_de_moyennes_ne_plante_pas(self, base_vierge):
        db = base_vierge
        self._preparer_notes(db)
        ia = _assistant()
        for _ in range(2):
            rep = ia.traiter("moyenne de la classe 6eme")
            assert "erreur" not in rep["texte"].lower()


class TestPresences:
    def test_absents_du_jour(self, base_vierge):
        import datetime
        db = base_vierge
        e1 = _ajouter_eleve(db, "Mambou", "Junior", "6eme")
        e2 = _ajouter_eleve(db, "Ngo", "Marie", "6eme", "F")
        aujourd_hui = datetime.date.today().isoformat()
        db.execute(
            "INSERT INTO presences (eleve_id, classe_id, date, statut) "
            "VALUES (?, ?, ?, 'Absent')",
            (e1, _classe_id(db, "6eme"), aujourd_hui))
        db.execute(
            "INSERT INTO presences (eleve_id, classe_id, date, statut) "
            "VALUES (?, ?, ?, 'Present')",
            (e2, _classe_id(db, "6eme"), aujourd_hui))
        ia = _assistant()
        rep = ia.traiter("qui est absent aujourd'hui ?")
        assert "Junior Mambou" in rep["texte"]
        assert "1" in rep["texte"] and ("absent" in rep["texte"].lower() or "élève" in rep["texte"] or "eleve" in rep["texte"])

    def test_personne_absent(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("qui est absent aujourd'hui ?")
        assert "Aucune absence" in rep["texte"] or "aucune absence" in rep["texte"].lower()


class TestCaisse:
    def test_solde_et_transactions_recentes(self, base_vierge):
        from repositories import repos
        repos.finance.add_transaction("entree", 50000, "Frais scolaires",
                                      "Scolarite", "Eleve Mambou")
        repos.finance.add_transaction("sortie", 12000, "Carburant",
                                      "Fonctionnement", "Moto")
        ia = _assistant()
        rep = ia.traiter("quel est le solde de la caisse ?")
        assert "50 000 FCFA" in rep["texte"]
        assert "38 000 FCFA" in rep["texte"]
        rep = ia.traiter("dernieres transactions")
        assert "Frais scolaires" in rep["texte"]
        assert "Solde actuel : 38 000 FCFA" in rep["texte"]


class TestTarifsEtPaiements:
    def test_tarifs_dune_classe(self, base_vierge):
        from repositories import repos
        cid = _classe_id(base_vierge, "6eme")
        repos.finance.add_tarif(cid, "Scolarite", 30000, "")
        repos.finance.add_tarif(cid, "Tenue", 5000, "")
        ia = _assistant()
        rep = ia.traiter("quels sont les tarifs de la classe 6eme ?")
        assert "Scolarite : 30 000 FCFA" in rep["texte"]
        assert "TOTAL des frais : 35 000 FCFA" in rep["texte"]

    def test_reste_a_payer_eleve(self, base_vierge):
        import datetime
        db = base_vierge
        from repositories import repos
        cid = _classe_id(db, "6eme")
        eid = _ajouter_eleve(db, "Mambou", "Junior", "6eme")
        repos.finance.add_tarif(cid, "Scolarite", 30000, "")
        db.execute(
            """INSERT INTO paiements (eleve_id, montant, type_frais,
               date_paiement) VALUES (?, ?, 'Scolarite', ?)""",
            (eid, 20000, datetime.date.today().isoformat()))
        ia = _assistant()
        rep = ia.traiter("combien a paye Mambou Junior ?")
        assert "20 000 FCFA" in rep["texte"]
        assert "Reste a payer : 10 000 FCFA" in rep["texte"]


class TestMoyenneGeneraleEtClassement:
    def _preparer(self, db):
        db.execute("INSERT OR IGNORE INTO matieres (nom, coefficient) "
                   "VALUES ('Maths', 1)")
        db.execute("INSERT OR IGNORE INTO matieres (nom, coefficient) "
                   "VALUES ('Francais', 3)")
        m1 = db.query_one("SELECT id FROM matieres WHERE nom = 'Maths'")["id"]
        m2 = db.query_one("SELECT id FROM matieres WHERE nom = 'Francais'")["id"]
        e1 = _ajouter_eleve(db, "Mambou", "Junior", "6eme")
        e2 = _ajouter_eleve(db, "Ngo", "Marie", "6eme", "F")
        for eid in (e1, e2):
            for mid in (m1, m2):
                db.execute(
                    """INSERT INTO notes (eleve_id, matiere_id, periode,
                       devoir1, devoir2, composition) VALUES (?, ?, ?, ?, ?, ?)""",
                    (eid, mid, "1er Trimestre", 10, 12, 14 if mid == m1 else 16))
        # Maths 12.5, Francais 16 -> generale ponderee 15.12
        return e1, e2

    def test_moyenne_generale_de_l_ecole(self, base_vierge):
        self._preparer(base_vierge)
        ia = _assistant()
        rep = ia.traiter("quelle est la moyenne generale ?")
        assert "13.00" in rep["texte"]
        assert "2" in rep["texte"] and ("élève" in rep["texte"] or "eleve" in rep["texte"])

    def test_classement_des_eleves(self, base_vierge):
        self._preparer(base_vierge)
        ia = _assistant()
        rep = ia.traiter("classement des eleves")
        assert "classement" in rep["texte"].lower() and "élève" in rep["texte"].lower()
        # Check that ranking shows both students
        assert "1." in rep["texte"] or "1)" in rep["texte"]

    def test_classement_de_la_classe(self, base_vierge):
        self._preparer(base_vierge)
        ia = _assistant()
        rep = ia.traiter("classement des eleves de 6eme")
        assert "6eme" in rep["texte"] or "6ème" in rep["texte"]
        assert "2" in rep["texte"] and ("élève" in rep["texte"] or "eleve" in rep["texte"]) or "1." in rep["texte"]

    def test_moyenne_generale_sans_notes(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("moyenne generale")
        assert "Aucune note" in rep["texte"]


class TestPaiementsGlobaux:
    def _payer(self, db, nom, prenom, montant):
        eid = _ajouter_eleve(db, nom, prenom, "6eme")
        db.execute(
            """INSERT INTO paiements (eleve_id, montant, type_frais,
               date_paiement) VALUES (?, ?, 'Scolarite', date('now'))""",
            (eid, montant))
        return eid

    def test_paiements_du_mois(self, base_vierge):
        self._payer(base_vierge, "Mambou", "Junior", 20000)
        self._payer(base_vierge, "Ngo", "Marie", 5000)
        ia = _assistant()
        rep = ia.traiter("combien ont paye ce mois ?")
        assert "2 versement(s)" in rep["texte"]
        assert "25 000 FCFA" in rep["texte"]

    def test_qui_paie_le_moins_et_le_plus(self, base_vierge):
        self._payer(base_vierge, "Mambou", "Junior", 20000)
        self._payer(base_vierge, "Ngo", "Marie", 5000)
        ia = _assistant()
        rep = ia.traiter("qui paie le moins ?")
        assert "le plus paye" in rep["texte"]
        assert "Marie Ngo" in rep["texte"]
        assert "Junior Mambou" in rep["texte"]

    def test_aucun_paiement(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("qui paie le moins ?")
        assert "Aucun paiement" in rep["texte"]


class TestRoles:
    def test_navigation_autorisee(self, base_vierge):
        ia = _assistant(DIRECTEUR)
        rep = ia.traiter("ouvre la caisse")
        assert rep["action"] == {"type": "navigate", "page": "caisse"}

    def test_gestionnaire_refuse_personnel(self, base_vierge):
        ia = _assistant(GESTIONNAIRE)
        rep = ia.traiter("ouvre le personnel")
        assert rep["action"] is None
        assert "ne permet pas" in rep["texte"]

    def test_gestionnaire_refuse_question_personnel(self, base_vierge):
        ia = _assistant(GESTIONNAIRE)
        rep = ia.traiter("combien d'enseignants ?")
        assert "ne permet pas" in rep["texte"]

    def test_gestionnaire_peut_creer_un_cycle(self, base_vierge):
        ia = _assistant(GESTIONNAIRE)
        rep = ia.traiter("creer un cycle Superieur")
        assert "Creer le cycle" in rep["texte"]
        rep = ia.traiter("oui")
        assert "cree avec succes" in rep["texte"]


class TestCreationsGuidees:
    def test_cycle_avec_demande_de_nom(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("creer un cycle")
        assert "Quel nom" in rep["texte"]
        rep = ia.traiter("Superieur")
        assert "Creer le cycle « Superieur »" in rep["texte"]
        assert rep["choix"] == ["Oui", "Non"]
        rep = ia.traiter("oui")
        assert "cree avec succes" in rep["texte"]
        assert base_vierge.query_one(
            "SELECT id FROM cycles WHERE nom = 'Superieur'")

    def test_cycle_doublon_message_clair(self, base_vierge):
        ia = _assistant()
        ia.traiter("creer un cycle Primaire")
        ia.traiter("Primaire")
        rep = ia.traiter("oui")
        assert "Echec" in rep["texte"]

    def test_annulation_cycle(self, base_vierge):
        ia = _assistant()
        ia.traiter("creer un cycle Test")
        ia.traiter("Test")
        rep = ia.traiter("non")
        assert "annulee" in rep["texte"].lower()
        assert not base_vierge.query_one(
            "SELECT id FROM cycles WHERE nom = 'Test'")

    def test_matiere_avec_coefficient(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("creer une matiere Histoire coefficient 2")
        assert "coefficient 2" in rep["texte"]
        rep = ia.traiter("oui")
        assert "Histoire » creee" in rep["texte"]
        ligne = base_vierge.query_one(
            "SELECT coefficient FROM matieres WHERE nom = 'Histoire'")
        assert ligne and ligne["coefficient"] == 2.0

    def test_classe_cycle_devine_et_resolu(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("creer une classe 6eme B")
        assert "College" in rep["texte"]
        rep = ia.traiter("oui")
        assert "creee" in rep["texte"]
        ligne = base_vierge.query_one(
            """SELECT c.id FROM classes c JOIN cycles cyc ON cyc.id = c.cycle_id
               WHERE c.nom = '6eme B' AND cyc.nom = 'College'""")
        assert ligne is not None

    def test_transaction_caisse_complete(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("enregistrer une entree de 5000 pour fournitures")
        assert "beneficiaire" in rep["texte"].lower()
        rep = ia.traiter("Association des parents")
        assert "ENTREE (recette)" in rep["texte"]
        assert "5 000 FCFA" in rep["texte"]
        rep = ia.traiter("oui")
        assert "enregistree" in rep["texte"]
        ligne = base_vierge.query_one(
            "SELECT * FROM transactions WHERE categorie = 'Assistant IA'")
        assert ligne is not None
        assert ligne["montant"] == 5000
        assert ligne["type"] == "entree"

    def test_transaction_annulee(self, base_vierge):
        ia = _assistant()
        ia.traiter("enregistrer une sortie de 3000 pour carburant")
        ia.traiter("-")
        ia.traiter("non")
        assert not base_vierge.query_one(
            "SELECT id FROM transactions WHERE categorie = 'Assistant IA'")


class TestMemoireApprentissage:
    def test_retiens_que_et_rappel(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("retiens que la reunion des parents est le samedi")
        assert "Retenu" in rep["texte"]
        rep = ia.traiter("quand a lieu la reunion des parents ?")
        assert "samedi" in rep["texte"]

    def test_quand_je_dis_reponds(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("quand je dis code secret reponds 1234")
        assert "Appris" in rep["texte"]
        rep = ia.traiter("code secret ?")
        assert "1234" in rep["texte"]

    def test_montre_memoire_et_oubli(self, base_vierge):
        ia = _assistant()
        ia.traiter("retiens que le portail ferme a 18h")
        rep = ia.traiter("montre ta memoire")
        assert "portail" in rep["texte"]
        rep = ia.traiter("oublie le portail")
        assert "Oublie" in rep["texte"]
        rep = ia.traiter("montre ta memoire")
        assert "vide" in rep["texte"].lower()

    def test_enseignement_guide_apres_echec(self, base_vierge):
        ia = _assistant()
        rep = ia.traiter("zxqv blorg fttn")
        assert "apprendre" in rep["texte"].lower()
        assert rep["choix"] == ["Oui", "Non"]
        rep = ia.traiter("oui")
        assert "reponse" in rep["texte"].lower()
        rep = ia.traiter("C'est la reponse magique 42")
        assert "retenu" in rep["texte"].lower()
        rep = ia.traiter("zxqv blorg fttn")
        assert "42" in rep["texte"]

    def test_refus_enseignement(self, base_vierge):
        ia = _assistant()
        ia.traiter("zxqv blorg fttn")
        rep = ia.traiter("non")
        assert "Pas de probleme" in rep["texte"]

    def test_oublie_tout_confirme(self, base_vierge):
        ia = _assistant()
        ia.traiter("retiens que le code vestiaire est 7777")
        rep = ia.traiter("oublie tout")
        assert rep["choix"] == ["Oui", "Non"]
        rep = ia.traiter("oui")
        assert "effacee" in rep["texte"].lower()
        rep = ia.traiter("montre ta memoire")
        assert "vide" in rep["texte"].lower()

    def test_memoire_partagee_entre_instances(self, base_vierge):
        ia1 = _assistant()
        ia1.traiter("retiens que l'uniforme est obligatoire le lundi")
        ia2 = _assistant()
        rep = ia2.traiter("uniforme du lundi ?")
        assert "obligatoire" in rep["texte"]


class TestLectureDonnees:
    def test_corpus_trouve_la_classe(self, base_vierge):
        db = base_vierge
        _ajouter_eleve(db, "Kimbembe", "Alain", "CM2")
        ia = _assistant()
        rep = ia.traiter("parle moi de Kimbembe Alain stp")
        assert ("Kimbembe" in rep["texte"]) or ("CM2" in rep["texte"])

    def test_reponse_structuree_sur_entrees_bizarres(self, base_vierge):
        ia = _assistant()
        for entree in ("!!!", "???", "a", "xyzzy qwerty asdf zxcvb nmlkj"):
            rep = ia.traiter(entree)
            assert set(rep.keys()) >= {"texte", "action"}
            assert isinstance(rep["texte"], str)


@pytest.fixture()
def mode_autonome(monkeypatch):
    """Force la synchro OFF, independamment de data/sync.json reel."""
    import core.network as network
    monkeypatch.setattr(network, "_sync_active", False)
    yield


class TestMultipostes:
    def test_etat_mode_autonome(self, base_vierge, mode_autonome):
        ia = _assistant()
        rep = ia.traiter("etat du serveur")
        assert "AUTONOME" in rep["texte"]
        assert rep["action"] == {"type": "ping_serveur"}

    def test_question_donnees_distantes_sans_serveur(self, base_vierge, mode_autonome):
        ia = _assistant()
        rep = ia.traiter("combien d'eleves sur le serveur ?")
        assert "Autonome" in rep["texte"] or "desactivee" in rep["texte"]


class TestAnneeActive:
    def test_annee_active_affichee(self, base_vierge):
        import datetime
        ia = _assistant()
        rep = ia.traiter("quelle annee scolaire est active ?")
        annee = datetime.date.today().year
        assert f"{annee}-{annee + 1}" in rep["texte"]


class TestFicheEleve:
    def test_fiche_complete(self, base_vierge):
        db = base_vierge
        eid = _ajouter_eleve(db, "Mambou", "Junior", "6eme")
        db.execute("UPDATE eleves SET pere_nom = 'Papa Mambou', pere_tel = '06 11 22 33 44' WHERE id = ?", (eid,))
        ia = _assistant()
        rep = ia.traiter("qui est Junior Mambou ?")
        assert "FICHE" in rep["texte"].upper() and "ÉLÈVE" in rep["texte"].upper()
        assert "Papa Mambou" in rep["texte"]

    def test_recherche_floue_nom_partiel(self, base_vierge):
        db = base_vierge
        _ajouter_eleve(db, "Mambou", "Junior", "6eme")
        ia = _assistant()
        rep = ia.traiter("fiche de mambou")
        assert "Mambou" in rep["texte"]


class TestExtrairePeriode:
    def test_mapping_trimestres(self):
        from services.assistant_ia import AssistantIA, PERIODES
        assert AssistantIA._extraire_periode("moyenne du 1er trimestre") == PERIODES[0]
        assert AssistantIA._extraire_periode("notes du deuxieme trimestre") == PERIODES[1]
        assert AssistantIA._extraire_periode("trimestre 3") == PERIODES[2]
        assert AssistantIA._extraire_periode("moyenne generale") is None
