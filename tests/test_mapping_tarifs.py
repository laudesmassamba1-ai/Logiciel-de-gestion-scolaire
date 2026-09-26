"""Correctifs C3/C4 : les tarifs annexes ne doivent ni etre effaces a
chaque pull (miroir destructeur) ni ecraser montant_pension au push.

Le serveur ne represente que Inscription / Scolarite : tout payload de
tarif d'un autre type est consommee localement (action "done"), sans
envoi et sans remplir la file d'attente.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestTypeSynchro:
    def test_types_principaux_synchronisables(self):
        from api.mapping import _type_frais_synchro
        assert _type_frais_synchro("Inscription")
        assert _type_frais_synchro("Scolarite")
        assert _type_frais_synchro("SCOLARITÉ")
        assert _type_frais_synchro("pension")

    def test_types_annexes_locaux(self):
        from api.mapping import _type_frais_synchro
        assert not _type_frais_synchro("Cantine")
        assert not _type_frais_synchro("Transport")
        assert not _type_frais_synchro("Tenue scolaire")
        assert _type_frais_synchro(None)


class TestRemapTarifs:
    def test_post_tarif_annexe_consomme_localement(self, monkeypatch):
        from api import mapping
        monkeypatch.setattr(mapping, "_liste", lambda *a, **k: [])
        r = mapping.remap("POST", "/tarifs-scolarite",
                          {"classe_nom": "6eme", "type_frais": "Cantine",
                           "montant": 5000, "annee_scolaire": ""})
        assert r == ("done",)

    def test_put_tarif_annexe_consomme_localement(self, monkeypatch):
        from api import mapping
        monkeypatch.setattr(mapping, "_liste", lambda *a, **k: [])
        r = mapping.remap("PUT", "/tarifs-scolarite/5",
                          {"classe_nom": "6eme", "type_frais": "Transport",
                           "montant": 8000, "annee_scolaire": ""})
        assert r == ("done",)

    def test_delete_tarif_annexe_consomme_localement(self, monkeypatch):
        from api import mapping
        monkeypatch.setattr(mapping, "_liste", lambda *a, **k: [])
        r = mapping.remap("DELETE", "/tarifs-scolarite/5",
                          {"classe_nom": "6eme", "type_frais": "Tenue",
                           "annee_scolaire": ""})
        assert r == ("done",)

    def test_post_scolarite_continue_vers_le_serveur(self, monkeypatch):
        """Les tarifs principaux gardent leur flux normal : ici la classe
        n'existe pas cote serveur => "skip" (cible inexistante), jamais
        "done" ni "send" vers une cible inconnue."""
        from api import mapping
        monkeypatch.setattr(mapping, "_liste", lambda *a, **k: [])
        r = mapping.remap("POST", "/tarifs-scolarite",
                          {"classe_nom": "6eme", "type_frais": "Inscription",
                           "montant": 5000, "annee_scolaire": "2026-2027"})
        assert r != ("done",)
        assert r[0] in ("send", "skip")