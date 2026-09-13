import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestCoherenceAnneeScolaire:
    """Garde temporelle : aucune ecriture datee hors annee scolaire active."""

    @pytest.fixture()
    def base_vierge(self, tmp_path, monkeypatch):
        data = tmp_path / "data"
        data.mkdir(parents=True)
        monkeypatch.setenv("GS_DATA_DIR", str(tmp_path))
        import database.db  # garantit le chargement du sous-module
        db_module = sys.modules["database.db"]
        monkeypatch.setattr(db_module, "DB_PATH", data / "ecole.db")
        monkeypatch.setattr(db_module, "DOCS_DIR", data / "documents")
        from database import db
        db._initialized = False
        db.init_db()
        yield db
        db._initialized = False

    def _definir_annee(self, db, libelle, debut, fin):
        db.execute("UPDATE annees_scolaires SET est_active = 0")
        return db.execute(
            "INSERT INTO annees_scolaires (libelle, date_debut, date_fin, est_active)"
            " VALUES (?, ?, ?, 1)", (libelle, debut, fin))

    def test_date_dans_annee_active_accepte_interieur(self, base_vierge):
        from ui.pages.helpers import date_dans_annee_active
        self._definir_annee(base_vierge, "2025-2026", "2025-09-01", "2026-06-30")
        assert date_dans_annee_active("2025-12-15") is True
        assert date_dans_annee_active("2025-09-01") is True  # bornes incluses
        assert date_dans_annee_active("2026-06-30") is True

    def test_date_hors_annee_active_refusee(self, base_vierge):
        from ui.pages.helpers import date_dans_annee_active
        self._definir_annee(base_vierge, "2025-2026", "2025-09-01", "2026-06-30")
        # Le cas remonte par l'utilisateur : annee recente activee,
        # saisies anterieures a la rentree.
        assert date_dans_annee_active("2020-10-05") is False
        assert date_dans_annee_active("2026-07-01") is False

    def test_transaction_rattachee_a_l_annee_active(self, base_vierge):
        self._definir_annee(base_vierge, "2024-2025", "2024-09-01", "2025-06-30")
        reference = repos_add_transaction()
        row = base_vierge.query_one(
            "SELECT * FROM transactions WHERE reference = ?", (reference,))
        assert row["annee_scolaire"] == "2024-2025"

    def test_filtrage_caisse_par_annee_conserve_l_historique_sans_annee(self, base_vierge):
        self._definir_annee(base_vierge, "2024-2025", "2024-09-01", "2025-06-30")
        repos_add_transaction()  # rattachee a 2024-2025
        # Ligne historique sans annee (saisies d'avant la migration).
        base_vierge.execute(
            "UPDATE transactions SET annee_scolaire = NULL")
        from repositories import repos
        filtre_actif = repos.transactions(annee="2024-2025")
        assert len(filtre_actif) == 1  # l'historique reste visible
        toutes = repos.transactions(annee=None)
        assert len(toutes) == 1


class TestCaissePaiements:
    """Chaque encaissement d'eleve doit apparaitre en Caisse.

    Cause racine : la Caisse ne lit que `transactions`, or un paiement
    n'y ecrivait pas -> un montant verse (ex. 15000) restait invisible.
    """

    @pytest.fixture()
    def base_avec_eleve(self, tmp_path, monkeypatch):
        data = tmp_path / "data"
        data.mkdir(parents=True)
        monkeypatch.setenv("GS_DATA_DIR", str(tmp_path))
        import database.db
        db_module = sys.modules["database.db"]
        monkeypatch.setattr(db_module, "DB_PATH", data / "ecole.db")
        monkeypatch.setattr(db_module, "DOCS_DIR", data / "documents")
        from database import db
        db._initialized = False
        db.init_db()

        classe_id = db.execute(
            "INSERT INTO classes (nom, cycle_id) VALUES (?, ?)", ("CP1", None))
        # Val, une eleve facturable (Scolarite tarif 15000).
        db.execute(
            "INSERT INTO tarifs (classe_id, type_frais, montant, annee_scolaire)"
            " VALUES (?, 'Scolarite', 15000, '2025-2026')", (classe_id,))
        eleve_id = db.execute(
            """INSERT INTO eleves (matricule, nom, prenom, sexe, classe_id,
                                   date_inscription)
               VALUES ('VAL-001', 'Attiogbe', 'Valerie', 'F', ?, '2025-09-10')""",
            (classe_id,))
        yield db, eleve_id
        db._initialized = False

    def test_paiement_cree_une_entree_de_caisse_liee(self, base_avec_eleve):
        db, eleve_id = base_avec_eleve
        from repositories import repos
        pid = repos.add_paiement(eleve_id, 15000, "Especes", "Scolarite",
                                 "2025-2026", "T1")
        rows = db.query("SELECT * FROM transactions WHERE paiement_id = ?",
                        (pid,))
        assert len(rows) == 1
        ecriture = rows[0]
        assert ecriture["montant"] == 15000
        assert ecriture["type"] == "entree"
        assert ecriture["categorie"] == "Scolarite"
        assert "Valerie" in ecriture["beneficiaire"]
        assert ecriture["annee_scolaire"] == "2025-2026"

    def test_caisse_affiche_le_paiement_recu(self, base_avec_eleve):
        db, eleve_id = base_avec_eleve
        from repositories import repos
        repos.add_paiement(eleve_id, 15000, "Especes", "Scolarite",
                           "2025-2026", "T1")
        # La Caisse (repos.transactions) voit donc l'encaissement.
        entrees = [r for r in repos.transactions() if r["type"] == "entree"]
        assert any(r["montant"] == 15000 for r in entrees)
        entree, sortie, solde = repos.caisse_totals()
        assert entree == 15000 and solde == 15000

    def test_supprimer_paiement_nete_vote_l_ecriture_de_caisse(self, base_avec_eleve):
        db, eleve_id = base_avec_eleve
        from repositories import repos
        pid = repos.add_paiement(eleve_id, 15000, "Especes", "Scolarite",
                                 "2025-2026", "T1")
        repos.delete_paiement(pid)
        assert db.query_one(
            "SELECT 1 FROM transactions WHERE paiement_id = ?", (pid,)) is None
        assert db.query_one(
            "SELECT 1 FROM paiements WHERE id = ?", (pid,)) is None

    def test_supprimer_l_ecriture_de_caisse_supprime_aussi_le_paiement(self,
                                                                       base_avec_eleve):
        db, eleve_id = base_avec_eleve
        from repositories import repos
        pid = repos.add_paiement(eleve_id, 15000, "Especes", "Scolarite",
                                 "2025-2026", "T1")
        ecriture = db.query_one(
            "SELECT * FROM transactions WHERE paiement_id = ?", (pid,))
        repos.delete_transaction(ecriture["id"])
        assert db.query_one(
            "SELECT 1 FROM paiements WHERE id = ?", (pid,)) is None
        assert db.query_one(
            "SELECT 1 FROM transactions WHERE id = ?",
            (ecriture["id"],)) is None

    def test_retropopulation_paiements_existants(self, base_avec_eleve):
        db, eleve_id = base_avec_eleve
        # Paiement deja enregistre AVANT le fix : aucune ecriture de caisse.
        old_pid = db.execute(
            """INSERT INTO paiements (eleve_id, montant, mode_reglement,
                                       type_frais, date_paiement,
                                       annee_scolaire, trimestre)
               VALUES (?, 15000, 'Especes', 'Scolarite', '2025-10-01',
                       '2025-2026', 'T1')""", (eleve_id,))
        # Simule l'ancien schema : transactions SANS colonne paiement_id,
        # avec une ligne de caisse preexistante non liee.
        db.execute("ALTER TABLE transactions RENAME TO transactions_historique")
        db.execute(
            """CREATE TABLE transactions (
                 id             INTEGER PRIMARY KEY AUTOINCREMENT,
                 date           TEXT NOT NULL DEFAULT (date('now', 'localtime')),
                 reference      TEXT NOT NULL,
                 beneficiaire   TEXT,
                 motif          TEXT,
                 categorie      TEXT,
                 montant        REAL NOT NULL,
                 type           TEXT NOT NULL,
                 mode_reglement TEXT)""")
        db.execute(
            """INSERT INTO transactions (date, reference, beneficiaire, motif,
                                          categorie, montant, type, mode_reglement)
               VALUES (date('now', 'localtime'), 'REC-VIEUX', 'Saisie manuelle',
                       'Frais', 'Scolarite', 5000, 'entree', 'Especes')""")
        db._initialized = False
        db.init_db()
        # La migration cree a posteriori l'ecriture de caisse du paiement...
        rows = db.query(
            "SELECT * FROM transactions WHERE paiement_id = ?", (old_pid,))
        assert len(rows) == 1
        assert rows[0]["montant"] == 15000
        assert rows[0]["type"] == "entree"
        # ... sans toucher aux lignes non liees.
        vieux = db.query_one(
            "SELECT * FROM transactions WHERE reference = ?", ("REC-VIEUX",))
        assert vieux["paiement_id"] is None


def repos_add_transaction():
    from repositories import repos
    return repos.add_transaction(
        "entree", 5000, "Droits de scolarite", "Scolarite",
        "Eleve Test", "Especes")
