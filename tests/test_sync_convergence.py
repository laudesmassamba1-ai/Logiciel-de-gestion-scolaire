"""Tests de convergence MySQL <-> SQLite : tombstones, atomicite, retry."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── fixtures de base ──────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _reset_singleton():
    from database.db import Database
    Database._instance = None
    yield
    Database._instance = None


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    import core.config
    import importlib
    db_mod = sys.modules.get("database.db") or importlib.import_module("database.db")
    monkeypatch.setattr(core.config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(core.config, "DOCS_DIR", tmp_path / "docs")

    Database = db_mod.Database
    Database._instance = None
    d = Database()
    d.init_db()
    yield d
    Database._instance = None


# ════════════════════════════════════════════════════════════════════════
# 1. DB singleton : __init__ idempotent (ne re-lance pas migration)
# ════════════════════════════════════════════════════════════════════════
class TestSingletonInit:
    def test_second_instantiation_does_not_reset_flags(self, test_db):
        """Un deuxieme Database() ne doit pas remettre _initialized=False."""
        from database.db import Database
        d1 = Database()
        d1.init_db()
        assert d1._initialized is True

        d2 = Database()
        # Après le 2e __init__, _initialized ne doit PAS etre remis a False
        assert d2._initialized is True


# ════════════════════════════════════════════════════════════════════════
# 2. Tombstone propagation : serveur -> client
# ════════════════════════════════════════════════════════════════════════
class TestTombstonePropagation:
    def test_delete_local_eleve_when_server_tombstones_it(self, test_db, monkeypatch):
        """Un eleve supprime cote serveur (est_supprime=1) est supprime
        en local par pull_donnees."""
        import services.sync_service as sync_mod
        from api import client as client_mod

        # Inserer un eleve local avec uuid
        test_db.execute(
            "INSERT INTO eleves (uuid_client, matricule, nom, prenom)"
            " VALUES (?, ?, ?, ?)",
            ("uuid-tomb-001", "ET001", "Dupont", "Jean"))
        eid = test_db.query_one(
            "SELECT id FROM eleves WHERE uuid_client = 'uuid-tomb-001'")["id"]

        # Ajouter une note et une presence associees
        matiere = test_db.execute(
            "INSERT INTO matieres (nom) VALUES (?)", ("Maths",))
        test_db.execute(
            "INSERT INTO notes (eleve_id, matiere_id, periode, devoir1)"
            " VALUES (?, ?, ?, ?)", (eid, matiere, "1er", 15))
        test_db.execute(
            "INSERT INTO presences (eleve_id, classe_id, date, statut)"
            " VALUES (?, ?, ?, ?)", (eid, None, "2025-09-01", "Absent"))

        # Mock API : eleves = [], eleves_supprimes = [uuid-tomb-001], autres = []
        monkeypatch.setattr(
            client_mod, "eleves",
            lambda: ([], None))
        monkeypatch.setattr(
            client_mod, "eleves_supprimes_syndication",
            lambda: ([{"uuid_client": "uuid-tomb-001"}], None))
        monkeypatch.setattr(client_mod, "enseignants", lambda: ([], None))
        monkeypatch.setattr(client_mod, "tous_les_programme", lambda: ([], None))
        monkeypatch.setattr(client_mod, "toutes_presence", lambda: ([], None))
        monkeypatch.setattr(client_mod, "note_syndication", lambda: ([], None))
        monkeypatch.setattr(client_mod, "paiement_syndication", lambda: ([], None))

        result = sync_mod.pull_donnees()

        # L'eleve + notes + presences ont ete supprimes
        assert test_db.query_one("SELECT id FROM eleves WHERE id = ?", (eid,)) is None
        assert test_db.query_one(
            "SELECT id FROM notes WHERE eleve_id = ?", (eid,)) is None
        assert test_db.query_one(
            "SELECT id FROM presences WHERE eleve_id = ?", (eid,)) is None
        assert result.get("suppressions", 0) >= 1

    def test_tombstone_does_not_delete_if_pending_queue(self, test_db, monkeypatch):
        """Un eleve qui a un POST PENDING (creation hors-ligne) n'est PAS
        supprime meme si le serveur le signale comme supprime."""
        import services.sync_service as sync_mod
        from api import client as client_mod

        test_db.execute(
            "INSERT INTO eleves (uuid_client, matricule, nom, prenom)"
            " VALUES (?, ?, ?, ?)",
            ("uuid-protect", "EP001", "Marie", "Louise"))

        # Enfiler un POST /eleve avec meme uuid
        test_db.enqueue(
            "POST", "/eleve",
            json.dumps({"uuid_client": "uuid-protect", "nom": "Marie"}),
            uuid_client="uuid-protect")

        monkeypatch.setattr(client_mod, "eleves", lambda: ([], None))
        monkeypatch.setattr(
            client_mod, "eleves_supprimes_syndication",
            lambda: ([{"uuid_client": "uuid-protect"}], None))
        monkeypatch.setattr(client_mod, "enseignants", lambda: ([], None))
        monkeypatch.setattr(client_mod, "tous_les_programme", lambda: ([], None))
        monkeypatch.setattr(client_mod, "toutes_presence", lambda: ([], None))
        monkeypatch.setattr(client_mod, "note_syndication", lambda: ([], None))
        monkeypatch.setattr(client_mod, "paiement_syndication", lambda: ([], None))

        sync_mod.pull_donnees()

        # L'eleve est conserve car un POST PENDING protege
        assert test_db.query_one(
            "SELECT id FROM eleves WHERE uuid_client = 'uuid-protect'") is not None

    def test_no_tombstone_endpoint_does_not_crash(self, test_db, monkeypatch):
        """Si le endpoint tombstone n'existe pas (vieux serveur), pull ne crash pas."""
        import services.sync_service as sync_mod
        from api import client as client_mod

        monkeypatch.setattr(client_mod, "eleves", lambda: ([], None))
        monkeypatch.setattr(
            client_mod, "eleves_supprimes_syndication",
            lambda: (None, "404 Not Found"))
        monkeypatch.setattr(client_mod, "enseignants", lambda: ([], None))
        monkeypatch.setattr(client_mod, "tous_les_programme", lambda: ([], None))
        monkeypatch.setattr(client_mod, "toutes_presence", lambda: ([], None))
        monkeypatch.setattr(client_mod, "note_syndication", lambda: ([], None))
        monkeypatch.setattr(client_mod, "paiement_syndication", lambda: ([], None))

        result = sync_mod.pull_donnees()
        # Pas d'erreur fatale
        assert "tombstones_eleves" not in [
            e.split(":")[0] for e in result.get("erreurs", [])]


# ════════════════════════════════════════════════════════════════════════
# 3. Mapping POST /eleve : resolution classe_id par classe_nom
# ════════════════════════════════════════════════════════════════════════
class TestMappingPostEleve:
    def test_resolves_classe_id_from_classe_nom(self):
        """POST /eleve avec classe_nom doit resoudre le classe_id serveur.

        La resolution passe par la LISTE /classe (comparaison normalisee,
        minuscules + sans accents) : l'ancienne route /classe/{nom} faisait
        un match SQL exact et raterait « 6eme » face a « 6eme B »."""
        from api import mapping

        def fake_request(method, path, **kwargs):
            if path == "/classe":
                return {"classes": [{"id": 10, "nom": "6eme"}]}, None
            return {}, None

        payload = {
            "nom": "Test", "prenom": "Eleve",
            "classe_nom": "6eme",
            "uuid_client": "uuid-test-resolve"
        }
        with patch("api.client._request", side_effect=fake_request):
            action = mapping.remap("POST", "/eleve", payload)

        assert action[0] == "send"
        assert action[1] == "/eleve"
        assert action[2]["classe_id"] == 10
        assert "classe_nom" not in action[2]

    def test_strips_local_classe_id_when_no_classe_nom(self):
        """POST /eleve sans classe_nom doit retirer le classe_id local."""
        from api import mapping

        payload = {"nom": "X", "prenom": "Y", "classe_id": 999}
        action = mapping.remap("POST", "/eleve", payload)
        assert action[0] == "send"
        assert "classe_id" not in action[2]


# ════════════════════════════════════════════════════════════════════════
# 4. Sync worker : enqueue reessayee (pas de perte silencieuse)
# ════════════════════════════════════════════════════════════════════════
class TestSyncWorkerEnqueue:
    def test_enqueue_marks_failed_not_done(self, test_db):
        """Quant mapping.remap renvoie 'enqueue', la ligne reste en file
        (FAILED) pour etre reessayee, et n'est PAS archivee (DONE)."""
        from api.sync_worker import SyncWorker

        # Inserer une operation en file
        qid = test_db.enqueue(
            "POST", "/test",
            json.dumps({"cle": "valeur"}))

        with patch("api.sync_worker.api_disponible", return_value=True), \
             patch("api.sync_worker.db", test_db), \
             patch("api.sync_worker._request", return_value=(None, None)), \
             patch("api.mapping.remap", return_value=("enqueue",)):
            worker = SyncWorker()
            worker._drain_queue()

        # La ligne doit etre FAILED (reessayable), PAS supprimee (DONE)
        row = test_db.query_one(
            "SELECT status FROM file_attente_synchro WHERE id = ?", (qid,))
        assert row is not None, "Ligne devrait encore exister (FAILED)"
        assert row["status"] == "FAILED"

    def test_skip_garde_la_ligne_pour_rejeu(self, test_db):
        """Quand mapping.remap renvoie 'skip' (cible pas encore sur le
        serveur), la ligne reste DANS la file et sera reessayee au cycle
        suivant : jamais de perte silencieuse."""
        from api.sync_worker import vider_file_attente

        qid = test_db.enqueue("PUT", "/noop", json.dumps({}))

        with patch("api.sync_worker.api_disponible", return_value=True), \
             patch("api.sync_worker.db", test_db), \
             patch("api.mapping.remap", return_value=("skip",)):
            vider_file_attente()

        row = test_db.query_one(
            "SELECT status FROM file_attente_synchro WHERE id = ?", (qid,))
        assert row is not None, "Ligne devrait rester en file (rejouee)"
        assert row["status"] == "PENDING"

    def test_skip_envoye_des_que_la_cible_est_la(self, test_db):
        """Une ligne 'skip' est envoyee des que le serveur connait la cible
        (le remap renvoie alors 'send')."""
        from api.sync_worker import vider_file_attente

        qid = test_db.enqueue("PUT", "/noop", json.dumps({}))

        with patch("api.sync_worker.api_disponible", return_value=True), \
             patch("api.sync_worker.db", test_db), \
             patch("api.mapping.remap", return_value=("skip",)):
            vider_file_attente()

        with patch("api.sync_worker.api_disponible", return_value=True), \
             patch("api.sync_worker.db", test_db), \
             patch("api.mapping.remap",
                   return_value=("send", "/noop", {"cle": "valeur"})), \
             patch("api.sync_worker._request", return_value=({}, None)):
            vider_file_attente()

        row = test_db.query_one(
            "SELECT id FROM file_attente_synchro WHERE id = ?", (qid,))
        assert row is None, "Ligne envoye avec succes = retiree de la file"


# ════════════════════════════════════════════════════════════════════════
# 5. Atomicite : delete_classe
# ════════════════════════════════════════════════════════════════════════
class TestDeleteClasseAtomicity:
    def test_all_related_rows_deleted_atomically(self, test_db, monkeypatch):
        """Supprimer une classe doit supprimer eleves, notes, presences,
        paiements, planning, tarifs, programmes et la classe elle-meme
        dans une seule transaction atomique."""
        monkeypatch.setattr(
            "core.network.sync_active", lambda: False)
        monkeypatch.setattr(
            "core.network.is_online", lambda: False)

        from repositories.classe_repository import ClasseRepository

        # Creer cycle + classe + eleves + notes + presences + paiements
        cid = test_db.execute(
            "INSERT INTO cycles (nom, description) VALUES (?, ?)",
            ("T", "test cycle"))
        classe_id = test_db.execute(
            "INSERT INTO classes (nom, cycle_id) VALUES (?, ?)",
            ("TEST-DEL", cid))
        eid = test_db.execute(
            "INSERT INTO eleves (matricule, nom, prenom, classe_id)"
            " VALUES (?, ?, ?, ?)",
            ("MDT001", "Del", "Test", classe_id))
        mat_id = test_db.execute(
            "INSERT INTO matieres (nom) VALUES (?)", ("M1",))
        test_db.execute(
            "INSERT INTO notes (eleve_id, matiere_id, periode, devoir1)"
            " VALUES (?, ?, ?, ?)", (eid, mat_id, "1er", 10))
        test_db.execute(
            "INSERT INTO presences (eleve_id, classe_id, date, statut)"
            " VALUES (?, ?, ?, ?)", (eid, classe_id, "2025-09-01", "Present"))
        test_db.execute(
            "INSERT INTO paiements (eleve_id, montant, mode_reglement, type_frais)"
            " VALUES (?, ?, ?, ?)", (eid, 50000, "espece", "Scolarite"))
        test_db.execute(
            "INSERT INTO planning (classe_id, jour, creneau, matiere, salle)"
            " VALUES (?, ?, ?, ?, ?)",
            (classe_id, "Lundi", "08h-10h", "M1", "Salle A"))
        test_db.execute(
            "INSERT INTO tarifs (classe_id, type_frais, montant)"
            " VALUES (?, ?, ?)", (classe_id, "Scolarite", 50000))
        test_db.execute(
            "INSERT INTO programmes (classe_id, matiere_id)"
            " VALUES (?, ?)", (classe_id, mat_id))

        repo = ClasseRepository()
        repo.delete_classe(classe_id)

        # Tout doit etre supprime
        assert test_db.query_one("SELECT id FROM classes WHERE id = ?",
                                 (classe_id,)) is None
        assert test_db.query_one("SELECT id FROM eleves WHERE id = ?",
                                 (eid,)) is None
        assert test_db.query_one("SELECT id FROM notes WHERE eleve_id = ?",
                                 (eid,)) is None
        assert test_db.query_one("SELECT id FROM presences WHERE eleve_id = ?",
                                 (eid,)) is None
        assert test_db.query_one(
            "SELECT id FROM planning WHERE classe_id = ?",
            (classe_id,)) is None


# ════════════════════════════════════════════════════════════════════════
# 6. Presence : delete fonctionne sans uuid_client
# ════════════════════════════════════════════════════════════════════════
class TestPresenceDelete:
    def test_delete_without_uuid_client(self, test_db, monkeypatch):
        """delete_presence doit fonctionner meme si l'eleve n'a pas de
        uuid_client (suppression locale pure)."""
        monkeypatch.setattr("core.network.sync_active", lambda: False)
        monkeypatch.setattr("core.network.is_online", lambda: False)

        from repositories.presence_repository import PresenceRepository

        eid = test_db.execute(
            "INSERT INTO eleves (matricule, nom, prenom)"
            " VALUES (?, ?, ?)", ("PN001", "No", "Uuid"))
        pid = test_db.execute(
            "INSERT INTO presences (eleve_id, date, statut)"
            " VALUES (?, ?, ?)", (eid, "2025-10-01", "Absent"))

        repo = PresenceRepository()
        repo.delete_presence(pid)

        assert test_db.query_one(
            "SELECT id FROM presences WHERE id = ?", (pid,)) is None


# ════════════════════════════════════════════════════════════════════════
# 7. Finance : add_paiement atomique
# ════════════════════════════════════════════════════════════════════════
class TestPaiementAtomicity:
    def test_paiement_and_caisse_created_together(self, test_db, monkeypatch):
        """add_paiement cree un paiement ET son ecriture de caisse en
        transaction atomique : les deux existent ou aucun n'existe."""
        monkeypatch.setattr("core.network.sync_active", lambda: False)
        monkeypatch.setattr("core.network.is_online", lambda: False)

        from repositories.finance_repository import FinanceRepository

        eid = test_db.execute(
            "INSERT INTO eleves (matricule, nom, prenom)"
            " VALUES (?, ?, ?)", ("FA001", "Fin", "Atom"))

        repo = FinanceRepository()
        pid = repo.add_paiement(eid, 25000, "espece", "Scolarite",
                                "2025-2026", "T1")

        # Paiement cree
        p = test_db.query_one("SELECT * FROM paiements WHERE id = ?", (pid,))
        assert p is not None
        assert p["montant"] == 25000

        # Correspondante en caisse
        cash = test_db.query_one(
            "SELECT * FROM transactions WHERE paiement_id = ?", (pid,))
        assert cash is not None
        assert cash["montant"] == 25000
        assert cash["type"] == "entree"
