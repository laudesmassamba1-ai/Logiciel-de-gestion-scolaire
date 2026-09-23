import sys
from pathlib import Path

import pytest

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db
from repositories import repos


@pytest.fixture()
def _base_isollee(tmp_path, monkeypatch):
    module_db = sys.modules["database.db"]
    monkeypatch.setattr(module_db, "DB_PATH", tmp_path / "test_utilitaires.db")
    db._initialized = False
    db.init_db()
    yield


class TestBlocNotes:
    def test_cycle_vie_note(self, _base_isollee):
        uid = 1
        n = repos.blocnote.notes(uid)
        assert n == []

        ajoute = repos.blocnote.ajouter(uid, "Recette cakes", "Farine + sucre")
        assert ajoute is not None

        notes = repos.blocnote.notes(uid)
        assert len(notes) == 1
        assert notes[0]["titre"] == "Recette cakes"
        assert notes[0]["contenu"] == "Farine + sucre"

        repos.blocnote.modifier(notes[0]["id"], "Recette cakes", "Farine + 2 oeufs")
        note = repos.blocnote.note(notes[0]["id"])
        assert note["contenu"] == "Farine + 2 oeufs"

        repos.blocnote.supprimer(notes[0]["id"])
        assert repos.blocnote.notes(uid) == []

    def test_notes_scopees_par_utilisateur(self, _base_isollee):
        repos.blocnote.ajouter(1, "A", "contenu A")
        repos.blocnote.ajouter(2, "B", "contenu B")
        assert len(repos.blocnote.notes(1)) == 1
        assert repos.blocnote.notes(1)[0]["titre"] == "A"
        assert len(repos.blocnote.notes(2)) == 1
        assert repos.blocnote.notes(2)[0]["titre"] == "B"


class TestAgenda:
    def test_evenements_du_jour(self, _base_isollee):
        uid = 1
        repos.agenda.ajouter(uid, "Conseil de classe",
                             "2026-09-20", "09:00", "Salle C", True)
        repos.agenda.ajouter(uid, "Reunion parents",
                             "2026-09-21", "17:30", "", False)
        du_jour = repos.agenda.evenements_du_jour(uid, "2026-09-20")
        assert len(du_jour) == 1
        assert du_jour[0]["titre"] == "Conseil de classe"
        assert du_jour[0]["alarme"] == 1

    def test_modifier_rearme_et_desactive_alarme(self, _base_isollee):
        uid = 1
        rede = repos.agenda.ajouter(uid, "Remise des bulletins",
                                    "2026-09-25", "08:00", "", True)
        ev = repos.agenda.evenements(uid)[0]
        repos.agenda.marquer_alarme_signalee(ev["id"])
        assert repos.agenda.evenements(uid)[0]["alarme_signalee"] == 1

        repos.agenda.modifier(ev["id"], "Remise des bulletins (modifie)",
                              "2026-09-25", "08:00", "", True)
        modifie = repos.agenda.evenements(uid)[0]
        assert modifie["titre"] == "Remise des bulletins (modifie)"
        assert modifie["alarme_signalee"] == 0

    def test_alarmes_dues_seulement_pour_horloge_passee(self, _base_isollee):
        import datetime
        passe = datetime.datetime.now() - datetime.timedelta(minutes=1)
        jour_passe = passe.strftime("%Y-%m-%d")
        heure_passe = passe.strftime("%H:%M")
        repos.agenda.ajouter(uid := 1, "Alarme passee (1 min)",
                             jour_passe, heure_passe, "", True)
        repos.agenda.ajouter(uid, "Alarme trop ancienne",
                             "2000-01-01", "00:01", "", True)
        repos.agenda.ajouter(uid, "Alarme future",
                             "2099-12-31", "23:59", "", True)
        dues = repos.agenda.alarmes_dues(uid)
        assert [e["titre"] for e in dues] == ["Alarme passee (1 min)"]

    def test_supprimer_evenement(self, _base_isollee):
        uid = 1
        repos.agenda.ajouter(uid, "Visite medecin", "2026-10-01", "10:00", "", False)
        ev = repos.agenda.evenements(uid)[0]
        repos.agenda.supprimer(ev["id"])
        assert repos.agenda.evenements(uid) == []