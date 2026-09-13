"""Dedoublonnage / rebasage des references entre le poste et le serveur.

Les repos poussent des ecritures « local-first » vers le serveur avec des
identifiants LOCAUX (local_id). Hors synchronisation multi-poste, ces ids ne
signifient rien pour le serveur : envoyer brut produirait des references
incorrectes (ex. cycle_id=5 alors que le serveur n'a que le cycle id=1).

Ce module, appele juste avant chaque envoi (donc aussi lors du vidage de la
file d'attente), resolve les references par cles naturelles (nom / uuid) et
construit un payload sur le serveur :

    * (« send », endpoint, payload)  -> envoyer maintenant (ids reattribues)
    * (« skip »,)                    -> la cible n'existe pas encore sur le
        serveur : on ne pousse pas (l'ecriture locale, elle, reste valide)
    * (« enqueue »,)                 -> le reseau a coupe pendant la
        resolution : on met en file, le drain reessaiera plus tard.

Les erreurs 404/400 lors de la resolution sont traitees comme « absent sur
le serveur » (skip) ; seules les erreurs reseau (hors ligne / 5xx) reenchetent.
"""

import re
import time
from urllib.parse import quote

_CACHE = {}
_TTL = 20.0


class _Reseau(Exception):
    pass


def _get(path):
    from api.client import _request
    data, err = _request("GET", path)
    if err:
        if err.startswith("API hors ligne") or err.startswith("Erreur API 5"):
            raise _Reseau(err)
        return None
    return data or {}


def _liste(key, path):
    data = _get(path)
    return (data or {}).get(key) or []


def _norm(valeur):
    return None if valeur is None else str(valeur).strip().casefold()


# ---------------------------------------------------------------------------
# Resolveurs par cles naturelles (returnent l'id serveur ou None)
# ---------------------------------------------------------------------------

def _cycle_id(nom):
    if not nom:
        return None
    cible = _norm(nom)
    for row in _liste("cycle", "/cycle"):
        if _norm(row.get("nom")) == cible:
            return row.get("id")
    return None


def _creer_cycle(nom):
    from api.client import _request
    data, err = _request("POST", "/cycle", json={"nom": nom, "description": ""})
    if err:
        raise _Reseau(err)
    return data.get("id") if data else None


def _cycle_id_ou_creer(nom):
    cid = _cycle_id(nom)
    if cid is None:
        cid = _creer_cycle(nom)
    return cid


def _cycle_sans_cycle():
    return _cycle_id_ou_creer("Sans cycle")


def _matiere_id(nom):
    if not nom:
        return None
    cible = _norm(nom)
    for row in _liste("matieres", "/matiere"):
        if _norm(row.get("nom")) == cible:
            return row.get("id")
    return None


def _classe_id(nom):
    if not nom:
        return None
    data = _get(f"/classe/{quote(str(nom))}")
    if not data:
        return None
    return (data.get("classe") or {}).get("id")


def _enseignant_id(nom_complet):
    if not nom_complet:
        return None
    cible = _norm(nom_complet)
    for row in _liste("enseignant", "/enseignant"):
        nom = row.get("nom") or ""
        prenom = row.get("prenom") or ""
        if f"{nom} {prenom}".strip() and _norm(f"{nom} {prenom}") == cible:
            return row.get("id")
        if _norm(nom) == _norm(nom_complet.split()[0]):
            return row.get("id")
    return None


def _eleve_id(uuid_client):
    if not uuid_client:
        return None
    cible = _norm(uuid_client)
    for row in _liste("eleves", "/eleve-syndication"):
        if _norm(row.get("uuid_client")) == cible:
            return row.get("id")
    return None


def _annee_id(libelle):
    if not libelle:
        return None
    cible = _norm(libelle)
    for row in _liste("annees_scolaires", "/lister_annees_scolaires"):
        if _norm(row.get("libelle")) == cible:
            return row.get("id")
    return None


def _programme_id(classe_nom, matiere_nom):
    if not classe_nom or not matiere_nom:
        return None
    data = _get(f"/programme/{quote(str(classe_nom))}")
    if not data:
        return None
    cible = _norm(matiere_nom)
    for row in (data.get("programme") or []):
        if _norm(row.get("matiere")) == cible:
            return row.get("id")
    return None


def _type_frais_role(type_frais):
    return "Inscription" if str(type_frais).strip().casefold() == "inscription" \
        else "Scolarite"


def _tarif_id(classe_nom, type_frais, annee_scolaire):
    if not classe_nom:
        return None
    role = _type_frais_role(type_frais)
    cible = _norm(classe_nom)
    annee = _norm(annee_scolaire) if annee_scolaire else None
    for row in _liste("tarifs", "/tarifs-scolarite"):
        if _norm(row.get("classe_nom")) != cible:
            continue
        if role == "Inscription" and not float(row.get("frais_inscription") or 0):
            continue
        if role == "Scolarite" and not float(row.get("montant_pension") or 0):
            continue
        if annee is not None and _norm(row.get("annee_scolaire")) != annee:
            continue
        return row.get("tarif_id")
    return None


def _pop(payload, cle):
    return payload.pop(cle, None)


# ---------------------------------------------------------------------------
# Coeur du remapper
# ---------------------------------------------------------------------------

def _remapper(method, endpoint, payload):
    if not isinstance(payload, dict):
        return (endpoint, payload)
    pl = dict(payload)

    # ---------- Classes ----------
    if method == "POST" and endpoint == "/classe":
        cycle_nom = _pop(pl, "cycle_nom")
        cid = _cycle_id_ou_creer(cycle_nom) if cycle_nom else _cycle_sans_cycle()
        if cid is None:
            return None
        pl["cycle_id"] = cid
        return (endpoint, pl)

    if method == "PUT" and endpoint.startswith("/modifierClasse/"):
        cid = _classe_id(_pop(pl, "classe_ancien_nom"))
        if cid is None:
            return None
        cycle_nom = _pop(pl, "cycle_nom")
        if cycle_nom is not None:
            sid = _cycle_id_ou_creer(cycle_nom) if cycle_nom else _cycle_sans_cycle()
            if sid is None:
                return None
            pl["cycle_id"] = sid
        pl.pop("cycle_id", None)
        return (f"/modifierClasse/{cid}", pl)

    if method == "DELETE" and endpoint.startswith("/supprimerClasse/"):
        nom = _pop(pl, "classe_nom")
        if not nom:
            return None
        return (f"/supprimerClasse/{quote(str(nom))}", pl)

    # ---------- Cycles ----------
    if method == "POST" and endpoint == "/cycle":
        if _cycle_id(pl.get("nom")) is not None:
            return None
        return (endpoint, pl)

    if method == "PUT" and endpoint.startswith("/modifierCycle/"):
        cid = _cycle_id(_pop(pl, "cycle_ancien_nom"))
        if cid is None:
            return None
        return (f"/modifierCycle/{cid}", pl)

    if method == "DELETE" and endpoint.startswith("/supprimerCycle/"):
        cid = _cycle_id(_pop(pl, "cycle_nom"))
        if cid is None:
            return None
        return (f"/supprimerCycle/{cid}", pl)

    # ---------- Matieres ----------
    if method == "POST" and endpoint == "/matiere":
        if _matiere_id(pl.get("nom")) is not None:
            return None
        return (endpoint, pl)

    if method == "PUT" and endpoint.startswith("/modifierMatiere/"):
        mid = _matiere_id(_pop(pl, "matiere_ancien_nom"))
        if mid is None:
            return None
        return (f"/modifierMatiere/{mid}", pl)

    if method == "DELETE" and endpoint.startswith("/supprimerMatiere/"):
        mid = _matiere_id(_pop(pl, "matiere_nom"))
        if mid is None:
            return None
        return (f"/supprimerMatiere/{mid}", pl)

    # ---------- Programmes ----------
    if method == "POST" and endpoint == "/associerMatiereClasseEnseignant":
        cid = _classe_id(_pop(pl, "classe_nom"))
        if cid is None:
            return None
        mid = _matiere_id(_pop(pl, "matiere_nom"))
        if mid is None:
            return None
        eid = _enseignant_id(_pop(pl, "enseignant_nom"))
        if eid is None:
            return None
        pl["classe_id"], pl["matiere_id"], pl["enseignant_id"] = cid, mid, eid
        return (endpoint, pl)

    if method == "PUT" and endpoint.startswith("/modifierProgramme/"):
        pid = _programme_id(_pop(pl, "classe_nom"), _pop(pl, "matiere_nom"))
        if pid is None:
            return None
        return (f"/modifierProgramme/{pid}", pl)

    if method == "DELETE" and endpoint.startswith("/supprimerProgramme/"):
        pid = _programme_id(_pop(pl, "classe_nom"), _pop(pl, "matiere_nom"))
        if pid is None:
            return None
        return (f"/supprimerProgramme/{pid}", pl)

    # ---------- Enseignants / Personnel ----------
    if method == "POST" and endpoint == "/enseignant":
        if _enseignant_id(pl.get("nom_complet")) is not None:
            return None
        return (endpoint, pl)

    if method == "PUT" and endpoint.startswith("/modifierEnseignant/"):
        eid = _enseignant_id(_pop(pl, "enseignant_nom"))
        if eid is None:
            return None
        return (f"/modifierEnseignant/{eid}", pl)

    if method == "DELETE" and endpoint.startswith("/supprimerEnseignant/"):
        eid = _enseignant_id(_pop(pl, "enseignant_nom"))
        if eid is None:
            return None
        return (f"/supprimerEnseignant/{eid}", pl)

    # ---------- Eleves ----------
    if method == "PUT" and endpoint.startswith("/modifierEleve/"):
        eid = _eleve_id(_pop(pl, "eleve_uuid"))
        if eid is None:
            return None
        if "classe_nom" in pl:
            cid = _classe_id(_pop(pl, "classe_nom"))
            if cid is not None:
                pl["classe_id"] = cid
        pl.pop("classe_id", None)
        return (f"/modifierEleve/{eid}", pl)

    if method == "DELETE" and re.match(r"^/eleve/\d+", endpoint):
        eid = _eleve_id(_pop(pl, "eleve_uuid"))
        if eid is None:
            return None
        return (re.sub(r"^/eleve/\d+", f"/eleve/{eid}", endpoint), pl)

    # ---------- Eleve : postes d'en-tete ----------
    if method == "POST" and endpoint in ("/paiement", "/note", "/presence"):
        return _remapper_transactionnel(method, endpoint, pl)

    # ---------- Obligatoire a re-placer : paiements / notes / presences ----
    if method == "POST" and endpoint == "/tarifs-scolarite":
        cid = _classe_id(_pop(pl, "classe_nom"))
        if cid is None:
            return None
        pl["classe_id"] = cid
        return (endpoint, pl)

    if method == "PUT" and endpoint.startswith("/tarifs-scolarite/"):
        tid = _tarif_id(_pop(pl, "classe_nom"), pl.get("type_frais"),
                        pl.get("annee_scolaire"))
        if tid is None:
            return None
        return (f"/tarifs-scolarite/{tid}", pl)

    if method == "DELETE" and endpoint.startswith("/tarifs-scolarite/"):
        tid = _tarif_id(_pop(pl, "classe_nom"), pl.get("type_frais"),
                        pl.get("annee_scolaire"))
        if tid is None:
            return None
        return (f"/tarifs-scolarite/{tid}", pl)

    # ---------- Planning ----------
    if method == "POST" and endpoint == "/planning":
        cid = _classe_id(_pop(pl, "classe_nom"))
        if cid is None:
            return None
        pl["classe_id"] = cid
        return (endpoint, pl)

    if method == "DELETE" and endpoint.startswith("/planning/"):
        cid = _classe_id(_pop(pl, "classe_nom"))
        if cid is None:
            return None
        return (f"/planning/{cid}", pl)

    # ---------- Annees scolaires ----------
    if method == "POST" and endpoint == "/ajouter_annee_scolaire":
        if _annee_id(pl.get("libelle")) is not None:
            return None
        return (endpoint, pl)

    if method == "PUT" and endpoint.startswith("/annee_scolaire/"):
        libelle = _pop(pl, "annee_ancien_libelle") or _pop(pl, "annee_libelle")
        aid = _annee_id(libelle)
        if aid is None:
            return None
        base = re.sub(r"^/annee_scolaire/\d+", f"/annee_scolaire/{aid}", endpoint)
        return (base, pl)

    if method == "DELETE" and endpoint.startswith("/annee_scolaire/"):
        aid = _annee_id(_pop(pl, "annee_libelle"))
        if aid is None:
            return None
        return (f"/annee_scolaire/{aid}", pl)

    # ---------- Tout le reste : envoi tel quel ----------
    return (endpoint, payload)


def _remapper_transactionnel(method, endpoint, pl):
    if endpoint == "/paiement":
        if "beneficiaire" in pl or pl.get("type") in ("entree", "sortie"):
            return (endpoint, pl)
        eid = _eleve_id(_pop(pl, "eleve_uuid"))
        if eid is None:
            return None
        if "classe_nom" in pl:
            cid = _classe_id(_pop(pl, "classe_nom"))
            if cid is None:
                return None
            pl.setdefault("classe_id", cid)
        pl["eleve_id"] = eid
        return (endpoint, pl)

    if endpoint == "/note":
        eid = _eleve_id(_pop(pl, "eleve_uuid"))
        if eid is None:
            return None
        mid = _matiere_id(_pop(pl, "matiere_nom"))
        if mid is None:
            return None
        pl["eleve_id"], pl["matiere_id"] = eid, mid
        return (endpoint, pl)

    if endpoint == "/presence":
        eid = _eleve_id(_pop(pl, "eleve_uuid"))
        if eid is None:
            return None
        cid = _classe_id(_pop(pl, "classe_nom"))
        if cid is None:
            return None
        pl["eleve_id"], pl["classe_id"] = eid, cid
        return (endpoint, pl)

    return (endpoint, pl)


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def remap(method, endpoint, payload):
    """Applique le rebasage des references au moment de l'envoi."""
    try:
        resultat = _remapper(method, endpoint, payload)
    except _Reseau:
        return ("enqueue",)
    except Exception:
        return ("enqueue",)
    if resultat is None:
        return ("skip",)
    return ("send", resultat[0], resultat[1])