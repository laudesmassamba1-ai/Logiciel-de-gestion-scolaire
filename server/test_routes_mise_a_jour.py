"""
Exercice des routes de mise a jour du serveur central (option B).

Charge server/main.py en mode SQLite, puis pilote :
  - GET /mise-a-jour/etat (inactif par defaut puis consigne activee) ;
  - GET /mise-a-jour/paquet/{nom} (depot central, anti-traversee).
Les consignes et paquets vivent dans GS_DATA_DIR (isole par fixture).
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_SERVER = Path(__file__).parent
sys.path.insert(0, str(_SERVER))


@pytest.fixture(scope="module")
def maj_client(tmp_path_factory):
    import sqlite_backend
    tmp = tmp_path_factory.mktemp("gs_maj")
    os.environ["GS_DB_MODE"] = "sqlite"
    os.environ["GS_SQLITE_DIR"] = str(tmp / "serveur")
    os.environ["GS_JWT_SECRET"] = "x" * 40
    os.environ["GS_DATA_DIR"] = str(tmp / "gsdata")
    sqlite_backend._SCHEMA_APPLIQUE = False

    _spec = importlib.util.spec_from_file_location(
        "serveur_maj", _SERVER / "main.py")
    serveur = importlib.util.module_from_spec(_spec)
    sys.modules["serveur_maj"] = serveur
    _spec.loader.exec_module(serveur)
    return TestClient(serveur.app, raise_server_exceptions=False)


def test_etat_inactif_par_defaut(maj_client):
    rep = maj_client.get("/mise-a-jour/etat")
    assert rep.status_code == 200
    assert rep.json()["actif"] is False


def test_paquet_inconnu_404(maj_client):
    assert maj_client.get("/mise-a-jour/paquet/inconnu.deb").status_code == 404


def test_traversee_repertoire_refusee(maj_client):
    rep = maj_client.get("/mise-a-jour/paquet/..%2FREADME.md")
    # Le nom est neutralise (basename) => jamais lu ailleurs qu'au depot.
    assert rep.status_code in (404, 422)


def test_consigne_activee_puis_telechargement(maj_client, tmp_path):
    from services import updater

    # Depot d'un paquet reel cote donnees partagees (GS_DATA_DIR).
    paquet = tmp_path / "gestion-scolaire_9.9.9_amd64.deb"
    contenu = b"contenu-du-paquet-999"
    paquet.write_bytes(contenu)
    info = updater.deposer_paquet(paquet)
    updater.ecrire_consigne("9.9.9", nom_paquet=info["nom"])

    rep = maj_client.get("/mise-a-jour/etat")
    assert rep.status_code == 200
    corps = rep.json()
    assert corps["actif"] is True
    assert corps["version"] == "9.9.9"

    rep = maj_client.get(f"/mise-a-jour/paquet/{info['nom']}")
    assert rep.status_code == 200
    assert rep.content == contenu

    # Nettoyage : la consigne ne doit pas polluer les autres tests.
    updater.desactiver_consigne()
    assert maj_client.get("/mise-a-jour/etat").json()["actif"] is False