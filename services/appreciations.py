"""Appreciations configurables par le directeur.

Stockee en JSON dans la table ``parametres`` (cle ``appreciations_config``).
Structure du JSON :
    {"paliers": [{"seuil": 16, "libelle": "Excellent"}, ...]}

Les paliers sont classes par ordre decroissant de seuil. La premiere regle
dont le seuil est inferieur ou egal a la moyenne determine l'appreciation.
"""

import json

from database import db

_CLE_CONFIG = "appreciations_config"

# Valeurs par defaut si le directeur n'a rien configure.
_DEFAULTS = [
    {"seuil": 16, "libelle": "Excellent"},
    {"seuil": 14, "libelle": "Tres bien"},
    {"seuil": 12, "libelle": "Bien"},
    {"seuil": 10, "libelle": "Assez bien"},
    {"seuil": 8, "libelle": "Passable"},
    {"seuil": 0, "libelle": "Insuffisant"},
]


def lire_config():
    """Retourne la liste des paliers (liste de dicts {seuil, libelle})."""
    try:
        row = db.query_one(
            "SELECT valeur FROM parametres WHERE cle = ?", (_CLE_CONFIG,))
    except Exception:
        return list(_DEFAULTS)
    if not row or not row["valeur"]:
        return list(_DEFAULTS)
    try:
        cfg = json.loads(row["valeur"])
        paliers = cfg.get("paliers", [])
        if not paliers:
            return list(_DEFAULTS)
        return paliers
    except (json.JSONDecodeError, TypeError):
        return list(_DEFAULTS)


def enregistrer_config(paliers):
    """Sauvegarde la liste des paliers [{seuil, libelle}, ...].
    Doit contenir au moins 1 palier. Les seuils sont arrondis a l'entier."""
    nettoyes = []
    for p in paliers:
        try:
            seuil = int(float(p.get("seuil", 0)))
            libelle = str(p.get("libelle", "")).strip()
        except (TypeError, ValueError):
            continue
        if libelle:
            nettoyes.append({"seuil": seuil, "libelle": libelle})
    if not nettoyes:
        nettoyes = list(_DEFAULTS)
    nettoyes.sort(key=lambda x: -x["seuil"])
    cfg_json = json.dumps({"paliers": nettoyes}, ensure_ascii=False)
    try:
        db.execute(
            "INSERT INTO parametres (cle, valeur) VALUES (?, ?) "
            "ON CONFLICT (cle) DO UPDATE SET valeur = excluded.valeur",
            (_CLE_CONFIG, cfg_json))
    except Exception:
        pass


def appreciation(moyenne):
    """Renvoie le libelle d'appreciation pour une moyenne donnee."""
    try:
        val = float(moyenne)
    except (TypeError, ValueError):
        return "-"
    paliers = lire_config()
    for p in paliers:
        if val >= p["seuil"]:
            return p["libelle"]
    return paliers[-1]["libelle"] if paliers else "Insuffisant"
