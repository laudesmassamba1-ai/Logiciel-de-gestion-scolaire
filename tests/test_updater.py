"""Tests du module services.updater (mises a jour distantes).

Couvre : comparaison de versions, choix du paquet selon la plateforme,
telechargement avec verification SHA-256, consigne/depot du serveur central,
et decision de verifier_mise_a_jour (serveur prime, sinon GitHub).
Tous les acces reseau sont simules (aucun appel externe).
"""

import hashlib
import os
import sys
from pathlib import Path

import pytest

import httpx
import importlib

_api_client_module = importlib.import_module("api.client")
from services import updater


@pytest.fixture(autouse=True)
def _donnees_iso(tmp_path, monkeypatch):
    monkeypatch.setenv("GS_DATA_DIR", str(tmp_path / "gsdata"))
    monkeypatch.setenv("GS_SYNC_ACTIVE", "false")
    yield


# ------------------------------------------------------------------ versions

def test_version_cle():
    assert updater.version_cle("v1.6.2") == (1, 6, 2)
    assert updater.version_cle("1.6.2") == (1, 6, 2)
    assert updater.version_cle("1.6") is None  # la convention exige 3 segments
    assert updater.version_cle("") is None
    assert updater.version_cle("abc") is None


def test_plus_recente():
    assert updater.plus_recente("v1.6.2", "1.6.1")
    assert updater.plus_recente("2.0.0", "1.9.9")
    assert not updater.plus_recente("v1.6.1", "1.6.1")
    assert not updater.plus_recente("v1.6.0", "1.6.1")
    assert not updater.plus_recente("bidon", "1.6.1")


# ----------------------------------------------------------- choix du paquet

def test_paquet_attendu_windows_setup(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert updater._paquet_attendu("1.6.2") == "GestionScolaire-Setup-1.6.2.exe"


def test_paquet_attendu_linux_deb(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(updater, "est_appimage", lambda: False)
    assert updater._paquet_attendu("1.6.2") == "gestion-scolaire_1.6.2_amd64.deb"


def test_paquet_attendu_linux_appimage(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(updater, "est_appimage", lambda: True)
    assert updater._paquet_attendu("1.6.2") == "GestionScolaire-1.6.2.AppImage"


def test_est_appimage_via_variable_APPIMAGE(monkeypatch):
    """Une AppImage montee par FUSE n'a pas argv[0] en .appimage : la
    detection doit reposer sur la variable d'environnement APPIMAGE."""
    monkeypatch.delenv("APPIMAGE", raising=False)
    monkeypatch.setattr(sys, "argv", ["/tmp/.mount_gestion/AppRun"])
    assert updater.est_appimage() is False

    monkeypatch.setenv("APPIMAGE", "/home/user/GestionScolaire-1.6.2.AppImage")
    assert updater.est_appimage() is True

    monkeypatch.delenv("APPIMAGE")
    monkeypatch.setattr(sys, "argv", ["/var/tmp/GestionScolaire-1.6.2.AppImage"])
    assert updater.est_appimage() is True


def test_choisir_asset(monkeypatch):
    assets = [
        {"name": "gestion-scolaire_1.6.2_amd64.deb", "browser_download_url": "u1"},
        {"name": "GestionScolaire-Setup-1.6.2.exe", "browser_download_url": "u2"},
        {"name": "GestionScolaire-1.6.2.AppImage", "browser_download_url": "u3"},
    ]
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(updater, "est_appimage", lambda: False)
    assert updater._choisir_asset(assets, "1.6.2")["name"].endswith(".deb")
    # Repli onefile Windows quand aucun Setup n'existe.
    monkeypatch.setattr(sys, "platform", "win32")
    onefile = [{"name": "GestionScolaire.exe", "browser_download_url": "u4"}]
    assert updater._choisir_asset(onefile, "1.6.2")["name"] == "GestionScolaire.exe"


# --------------------------------------------------- consigne / depot (option B)

def test_consigne_cycle(tmp_path):
    assert updater.lire_consigne() == {}
    updater.ecrire_consigne("1.6.2", nom_paquet="gestion-scolaire_1.6.2_amd64.deb")
    consigne = updater.lire_consigne()
    assert consigne["actif"] is True
    assert consigne["version"] == "1.6.2"
    assert consigne["paquet_linux"] == "gestion-scolaire_1.6.2_amd64.deb"
    assert "sha256" not in consigne


def test_consigne_diffuse_sha256(tmp_path):
    """L'empreinte du paquet depose doit rejoindre la consigne (integrite)."""
    source = tmp_path / "gestion-scolaire_1.6.2_amd64.deb"
    source.write_bytes(b"contenu-paquet")
    info = updater.deposer_paquet(source)
    updater.ecrire_consigne("1.6.2", nom_paquet=info["nom"],
                            sha256={info["nom"]: info["sha256"]})
    consigne = updater.lire_consigne()
    assert consigne["sha256"][info["nom"]] == info["sha256"]


def test_desactiver_consigne_purge_tout(tmp_path):
    source = tmp_path / "gestion-scolaire_1.6.2_amd64.deb"
    source.write_bytes(b"contenu-paquet")
    info = updater.deposer_paquet(source)
    updater.ecrire_consigne("1.6.2", nom_paquet=info["nom"],
                            sha256={info["nom"]: info["sha256"]})
    updater.desactiver_consigne()
    consigne = updater.lire_consigne()
    assert consigne["actif"] is False
    assert not consigne.get("paquet_linux")
    assert "sha256" not in consigne


def test_deposer_paquet(tmp_path):
    source = tmp_path / "paquet.deb"
    source.write_bytes(b"contenu-paquet")
    info = updater.deposer_paquet(source)
    assert info["nom"] == "paquet.deb"
    assert info["sha256"] == hashlib.sha256(b"contenu-paquet").hexdigest()
    depose = updater.dossier_depot_serveur() / "paquet.deb"
    assert depose.exists()
    assert depose.read_bytes() == b"contenu-paquet"


# ----------------------------------------------------------- scripts d'installation

def test_style_script_windows(monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    assert updater._style_script() == ("\r\n", "cp1252")


def test_style_script_linux(monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    assert updater._style_script() == ("\n", "utf-8")


def test_ecrire_script_linux_lf_executable(monkeypatch, tmp_path):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(updater, "dossier_mises_a_jour", lambda: tmp_path)
    chemin = updater._ecrire_script("maj.sh", ["#!/bin/sh", "true"], shell=True)
    assert chemin.read_bytes() == b"#!/bin/sh\ntrue\n"
    assert os.access(chemin, os.X_OK)


# --------------------------------------------------------------- telechargement

class _FausseReponse:
    def __init__(self, contenu, status=200):
        self._contenu = contenu
        self.status_code = status
        self.headers = {"content-length": str(len(contenu))}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("erreur", request=None, response=None)

    def iter_bytes(self, taille):
        yield self._contenu


class _Contexte:
    def __init__(self, reponse):
        self._reponse = reponse

    def __enter__(self):
        return self._reponse

    def __exit__(self, *exc):
        return False


def _mocker_stream(monkeypatch, contenu, status=200):
    def _fake_stream(method, url, **kwargs):
        return _Contexte(_FausseReponse(contenu, status))
    monkeypatch.setattr(httpx, "stream", _fake_stream)


def test_telecharger_ok_sha_valide(monkeypatch, tmp_path):
    contenu = b"paquet-ok"
    _mocker_stream(monkeypatch, contenu)
    infos = {
        "nom_fichier": "GestionScolaire-Setup-1.6.2.exe",
        "url": "https://exemple/paquet",
        "sha256": hashlib.sha256(contenu).hexdigest(),
    }
    chemin, erreur = updater.telecharger(infos)
    assert erreur is None
    assert Path(chemin).exists()
    assert Path(chemin).read_bytes() == contenu


def test_telecharger_sha_invalide(monkeypatch):
    contenu = b"paquet-corrompu"
    _mocker_stream(monkeypatch, contenu)
    infos = {
        "nom_fichier": "maj.deb",
        "url": "https://exemple/paquet",
        "sha256": "0" * 64,
    }
    chemin, erreur = updater.telecharger(infos)
    assert chemin is None
    assert "SHA-256" in erreur
    assert not (updater.dossier_mises_a_jour() / "maj.deb").exists()


def test_telecharger_erreur_serveur(monkeypatch):
    _mocker_stream(monkeypatch, b"", status=404)
    chemin, erreur = updater.telecharger({"nom_fichier": "x.deb", "url": "u"})
    assert chemin is None
    assert "Telechargement" in erreur


def test_telecharger_progression(monkeypatch):
    contenu = b"abcdef"
    _mocker_stream(monkeypatch, contenu)
    recu_total = []
    updater.telecharger(
        {"nom_fichier": "p.deb", "url": "u"},
        progression=lambda r, t: recu_total.append((r, t)))
    assert recu_total and recu_total[-1][0] == len(contenu)


# --------------------------------------------------------------- sources (A/B)

class _FausseRelease:
    """Instance repondant comme l'API GitHub : .raise_for_status() puis .json()."""

    def __init__(self, **kwargs):
        self._donnees = dict(kwargs)

    def raise_for_status(self):
        return None

    def json(self):
        return dict(self._donnees)


def _fausse_release_github(**kwargs):
    return _FausseRelease(**kwargs)


def test_cible_github_rien_de_nouveau(monkeypatch):
    monkeypatch.setattr(
        httpx, "get",
        lambda *a, **k: _fausse_release_github(tag_name="v1.6.1", assets=[]))
    assert updater.cible_github() is None


def test_cible_github_plus_recente(monkeypatch):
    assets = [{"name": "GestionScolaire-Setup-9.9.9.exe",
               "browser_download_url": "https://x/setup.exe"}]
    monkeypatch.setattr(
        httpx, "get",
        lambda *a, **k: _fausse_release_github(tag_name="v9.9.9", assets=assets))
    monkeypatch.setattr(updater, "_sha256_depuis_assets", lambda a, n: None)
    monkeypatch.setattr(sys, "platform", "win32")
    infos = updater.cible_github()
    assert infos is not None
    assert infos["source"] == "github"
    assert infos["version_texte"] == "9.9.9"
    assert infos["url"] == "https://x/setup.exe"


def test_cible_github_hors_ligne(monkeypatch):
    def _explose(*a, **k):
        raise httpx.ConnectError("hors ligne")
    monkeypatch.setattr(httpx, "get", _explose)
    assert updater.cible_github() is None


def test_cible_serveur_active(monkeypatch):
    monkeypatch.setattr(updater, "SYNC_ACTIVE", True)
    nom_paquet = (
        "GestionScolaire-Setup-9.9.9.exe"
        if (sys.platform or "").lower().startswith("win")
        else "gestion-scolaire_9.9.9_amd64.deb"
    )
    infos = {
        "actif": True, "version": "9.9.9", "obligatoire": True,
        "paquet_linux": "gestion-scolaire_9.9.9_amd64.deb",
        "paquet_windows": "GestionScolaire-Setup-9.9.9.exe",
        "sha256": {nom_paquet: "abc"},
    }
    monkeypatch.setattr(_api_client_module, "_request",
                        lambda method, path, **k: (infos, None))
    cible = updater.cible_serveur()
    assert cible is not None
    assert cible["source"] == "serveur"
    assert cible["version_texte"] == "9.9.9"
    assert cible["obligatoire"] is True
    assert cible["url"].endswith("/mise-a-jour/paquet/" + nom_paquet)


def test_cible_serveur_inactive(monkeypatch):
    monkeypatch.setattr(updater, "SYNC_ACTIVE", True)
    monkeypatch.setattr(_api_client_module, "_request",
                        lambda method, path, **k: ({"actif": False}, None))
    assert updater.cible_serveur() is None


def test_cible_serveur_sans_sync(monkeypatch):
    monkeypatch.setattr(updater, "SYNC_ACTIVE", False)

    def _inattendu(method, path, **k):
        pytest.fail("_request ne doit pas etre appele sans synchronisation")

    monkeypatch.setattr(_api_client_module, "_request", _inattendu)
    assert updater.cible_serveur() is None


def test_verifier_serveur_prime(monkeypatch):
    monkeypatch.setattr(updater, "SYNC_ACTIVE", True)
    monkeypatch.setattr(_api_client_module, "_request",
                        lambda method, path, **k: (
                            {"actif": True, "version": "9.9.9",
                             "paquet_linux": "", "paquet_windows": ""}, None))
    cible = updater.verifier_mise_a_jour()
    assert cible is not None and cible["source"] == "serveur"


def test_verifier_repli_github(monkeypatch):
    monkeypatch.setattr(updater, "SYNC_ACTIVE", False)
    monkeypatch.setattr(updater, "cible_github", lambda: {"source": "github"})
    assert updater.verifier_mise_a_jour()["source"] == "github"


def test_blocage_obligatoire():
    assert updater.blocage_obligatoire(
        {"source": "serveur", "obligatoire": True})
    assert not updater.blocage_obligatoire(
        {"source": "github", "obligatoire": False})


# ----------------------------------------------------------------- installation

def _paquet_tmp(tmp_path, nom, contenu=b"contenu"):
    chemin = tmp_path / nom
    chemin.write_bytes(contenu)
    return str(chemin)


def test_installer_windows_avec_deb_refuse(monkeypatch, tmp_path):
    """Jamais de .deb installe sur Windows (protection logique)."""
    monkeypatch.setattr(updater, "est_appimage", lambda: False)
    monkeypatch.setattr(sys, "platform", "win32")
    action, message = updater.installer(
        _paquet_tmp(tmp_path, "gestion-scolaire_1.6.2_amd64.deb"), {})
    assert action == "erreur"
    assert ".exe" in message


def test_installer_linux_avec_exe_refuse(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "est_appimage", lambda: False)
    monkeypatch.setattr(sys, "platform", "linux")
    action, message = updater.installer(
        _paquet_tmp(tmp_path, "GestionScolaire-Setup-1.6.2.exe"), {})
    assert action == "erreur"
    assert ".deb" in message or ".AppImage" in message


def test_installer_windows_setup_lance(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "est_appimage", lambda: False)
    monkeypatch.setattr(sys, "platform", "win32")
    lance = []
    monkeypatch.setattr(updater, "_script_windows_setup", lambda c: Path(c))
    monkeypatch.setattr(updater, "_lancer_detache", lambda cmd: lance.append(cmd))
    action, _ = updater.installer(
        _paquet_tmp(tmp_path, "GestionScolaire-Setup-1.6.2.exe"), {})
    assert action == "fermer" and lance


def test_installer_windows_onefile_lance(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "est_appimage", lambda: False)
    monkeypatch.setattr(sys, "platform", "win32")
    lance = []
    monkeypatch.setattr(updater, "_script_windows_onefile", lambda c, ci: Path(c))
    monkeypatch.setattr(updater, "_lancer_detache", lambda cmd: lance.append(cmd))
    action, _ = updater.installer(
        _paquet_tmp(tmp_path, "GestionScolaire.exe"), {})
    assert action == "fermer" and lance


def test_installer_linux_deb_lance(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "est_appimage", lambda: False)
    monkeypatch.setattr(sys, "platform", "linux")
    lance = []
    monkeypatch.setattr(updater, "_script_linux_deb", lambda c: Path(c))
    monkeypatch.setattr(updater, "_lancer_detache", lambda cmd: lance.append(cmd))
    action, _ = updater.installer(
        _paquet_tmp(tmp_path, "gestion-scolaire_1.6.2_amd64.deb"), {})
    assert action == "fermer" and lance


def test_installer_appimage_remplace(monkeypatch, tmp_path):
    """AppImage : remplacement atomique de l'archive (variable APPIMAGE)."""
    monkeypatch.setattr(updater, "est_appimage", lambda: True)
    cible = tmp_path / "GestionScolaire-1.6.1.AppImage"
    cible.write_bytes(b"ancienne")
    monkeypatch.setenv("APPIMAGE", str(cible))
    action, _ = updater.installer(
        _paquet_tmp(tmp_path, "GestionScolaire-1.6.2.AppImage", b"nouvelle"), {})
    assert action == "fait"
    assert cible.read_bytes() == b"nouvelle"