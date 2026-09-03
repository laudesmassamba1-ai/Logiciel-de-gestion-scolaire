"""
Synchronisation DESCENDANTE : MySQL -> SQLite.
À appeler dès qu'il y a internet, pour rafraîchir tout le cache local
(tables de référence ET tables d'action) avec les dernières données
du serveur — y compris ce que d'autres postes ont ajouté entre-temps.

⚠️ Vérifie les noms de clés JSON ci-dessous (ex: "classes", "presences",
"inscriptions") contre ce que tes routes renvoient réellement, surtout
pour les 3 routes que tu viens d'ajouter/corriger toi-même.
"""

import requests
from database import upsert_reference, upsert_action_row

TIMEOUT = 5


def _get(base_url, endpoint):
    try:
        r = requests.get(f"{base_url}{endpoint}", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[PULL] Échec sur {endpoint} : {e}")
        return None


# ============================================================
# TABLES DE RÉFÉRENCE
# ============================================================

def pull_cycle(base_url):
    data = _get(base_url, "/cycle")
    if not data:
        return
    lignes = [(c["id"], c["nom"]) for c in data.get("cycle", [])]
    upsert_reference("cycle", ["id", "nom"], lignes)
    print(f"[PULL] {len(lignes)} cycle(s) synchronisé(s).")


def pull_classe(base_url):
    # ⚠️ Suppose que ta route corrigée renvoie {"classes": [{"id":..,"classe" ou "nom":..,"cycle_id":..}, ...]}
    data = _get(base_url, "/classe")
    if not data:
        return
    lignes = []
    for c in data.get("classes", []):
        nom = c.get("nom") or c.get("classe")
        lignes.append((c["id"], nom, c["cycle_id"]))
    upsert_reference("classe", ["id", "nom", "cycle_id"], lignes)
    print(f"[PULL] {len(lignes)} classe(s) synchronisée(s).")


def pull_matiere(base_url):
    data = _get(base_url, "/matiere")
    if not data:
        return
    lignes = [(m["id"], m["nom"]) for m in data.get("matieres", [])]
    upsert_reference("matiere", ["id", "nom"], lignes)
    print(f"[PULL] {len(lignes)} matière(s) synchronisée(s).")


def pull_annee_scolaire(base_url):
    data = _get(base_url, "/lister_annees_scolaires")
    if not data:
        return
    lignes = [
        (a["id"], a["libelle"], a.get("date_debut"), a.get("date_fin"), int(a.get("est_active", 0)))
        for a in data.get("annees_scolaires", [])
    ]
    upsert_reference(
        "annee_scolaire",
        ["id", "libelle", "date_debut", "date_fin", "est_active"],
        lignes,
    )
    print(f"[PULL] {len(lignes)} année(s) scolaire(s) synchronisée(s).")


def pull_enseignant(base_url):
    data = _get(base_url, "/enseignant")
    if not data:
        return
    lignes = [
        (e["id"], e["nom"], e["prenom"], e.get("sexe"), e.get("telephone"), e.get("email"), e.get("statut"))
        for e in data.get("enseignant", [])
    ]
    upsert_reference(
        "enseignant",
        ["id", "nom", "prenom", "sexe", "telephone", "email", "statut"],
        lignes,
    )
    print(f"[PULL] {len(lignes)} enseignant(s) synchronisé(s).")


def pull_utilisateurs(base_url):
    data = _get(base_url, "/utilisateurs")
    if not data:
        return
    # Cette route renvoie une liste directement, pas d'enveloppe
    liste = data if isinstance(data, list) else data.get("utilisateurs", [])
    lignes = [
        (u["id"], u["nom"], u["prenom"], u.get("telephone"), u.get("email"), u.get("role"), u.get("statut"))
        for u in liste
    ]
    upsert_reference(
        "utilisateur",
        ["id", "nom", "prenom", "telephone", "email", "role", "statut"],
        lignes,
    )
    print(f"[PULL] {len(lignes)} utilisateur(s) synchronisé(s).")


def pull_tarifs(base_url):
    data = _get(base_url, "/tarifs-scolarite")
    if not data:
        return
    liste = data if isinstance(data, list) else data.get("tarifs", [])
    lignes = [
        (t.get("tarif_id", t.get("id")), t.get("classe_id"), t.get("annee_scolaire_id"),
         t.get("frais_inscription"), t.get("montant_pension"))
        for t in liste
    ]
    upsert_reference(
        "tarif_scolarite",
        ["id", "classe_id", "annee_scolaire_id", "frais_inscription", "montant_pension"],
        lignes,
    )
    print(f"[PULL] {len(lignes)} tarif(s) synchronisé(s).")


def pull_programme(base_url):
    # ⚠️ Suppose que tu as ajouté GET /programme (toutes classes confondues)
    data = _get(base_url, "/tous_les_programme")
    if not data:
        return
    liste = data.get("programme", []) if isinstance(data, dict) else data
    lignes = [
        (p.get("id"), p.get("classe_id"), p.get("matiere_id"),
         p.get("enseignant_id"), p.get("coefficient", 1))
        for p in liste
    ]
    upsert_reference(
        "programme",
        ["id", "classe_id", "matiere_id", "enseignant_id", "coefficient"],
        lignes,
    )
    print(f"[PULL] {len(lignes)} ligne(s) de programme synchronisée(s).")


# ============================================================
# TABLES D'ACTION — upsert COMPLET (pas juste réconciliation) :
# toute ligne venant du serveur est copiée en local, qu'elle ait
# été créée hors ligne, directement en MySQL, ou par un autre poste.
# ============================================================

def pull_eleve(base_url):
    data = _get(base_url, "/eleve")
    if not data:
        return
    eleves = data.get("eleves", [])
    for e in eleves:
        upsert_action_row(
            "eleve",
            id_serveur=e["id"],
            uuid_client=e.get("uuid_client"),
            colonnes_valeurs={
                "nom": e.get("nom"),
                "prenom": e.get("prenom"),
                "sexe": e.get("sexe"),
                "date_naissance": e.get("date_naissance"),
                "lieu_naissance": e.get("lieu_naissance"),
                "adresse": e.get("adresse"),
                "nom_parent": e.get("nom_parent"),
                "redoublant": e.get("redoublant", "0"),
                "statut": e.get("statut"),
                "telephone_parent": e.get("numero_parent") or e.get("telephone_parent"),
                "est_supprime": int(e.get("est_supprime", 0)),
            },
        )
    print(f"[PULL] {len(eleves)} élève(s) synchronisé(s).")


def pull_paiement(base_url):
    data = _get(base_url, "/paiement")
    if not data:
        return
    paiements = data.get("paiement", [])
    for p in paiements:
        upsert_action_row(
            "paiement",
            id_serveur=p["id"],
            uuid_client=p.get("uuid_client"),
            colonnes_valeurs={
                "inscription_id": p.get("inscription_id"),
                "type_frais": p.get("type_frais"),
                "montant": p.get("montant"),
                "date_paiement": p.get("date_paiement"),
                "mode_paiement": p.get("mode_paiement"),
                "trimestre": p.get("trimestre"),
                "mois": p.get("mois"),
            },
        )
    print(f"[PULL] {len(paiements)} paiement(s) synchronisé(s).")


def pull_note(base_url):
    data = _get(base_url, "/note")
    if not data:
        return
    notes = data.get("note", [])
    for n in notes:
        upsert_action_row(
            "note",
            id_serveur=n["id"],
            uuid_client=n.get("uuid_client"),
            colonnes_valeurs={
                "inscription_id": n.get("inscription_id"),
                "matiere_id": n.get("matiere_id"),
                "type_evaluation": n.get("type_evaluation"),
                "note": n.get("note"),
                "note_sur": n.get("note_sur", 20),
                "date_evaluation": n.get("date_evaluation"),
                "trimestre": n.get("trimestre"),
            },
        )
    print(f"[PULL] {len(notes)} note(s) synchronisée(s).")


def pull_presences(base_url):
    # ⚠️ Suppose que ta nouvelle route renvoie {"presences": [...]}
    data = _get(base_url, "/toutes_presence")
    if not data:
        return
    presences = data.get("presences", [])
    for p in presences:
        upsert_action_row(
            "presences",
            id_serveur=p["id"],
            uuid_client=p.get("uuid_client"),
            colonnes_valeurs={
                "eleve_id_serveur": p.get("eleve_id"),
                "classe_id": p.get("classe_id"),
                "date_presence": p.get("date_presence"),
                "statut": p.get("statut"),
                "justifie": p.get("justifie", "Non"),
            },
        )
    print(f"[PULL] {len(presences)} présence(s) synchronisée(s).")


def pull_inscription(base_url):
    # ⚠️ Suppose que ta nouvelle route renvoie {"inscriptions": [...]}
    data = _get(base_url, "/lister_toutes_les_inscriptions")
    if not data:
        return
    inscriptions = data.get("inscriptions", [])
    for i in inscriptions:
        upsert_action_row(
            "inscription",
            id_serveur=i["id"],
            uuid_client=i.get("uuid_client"),
            colonnes_valeurs={
                "eleve_id_serveur": i.get("eleve_id"),
                "classe_id": i.get("classe_id"),
                "annee_scolaire_id": i.get("annee_scolaire_id"),
                "statut": i.get("statut", "actif"),
            },
        )
    print(f"[PULL] {len(inscriptions)} inscription(s) synchronisée(s).")


# ============================================================
# POINT D'ENTRÉE : tout rafraîchir d'un coup
# ============================================================

def synchroniser_tout_depuis_mysql(base_url):
    print("[PULL] Rafraîchissement complet depuis MySQL...")

    # Références d'abord (pour respecter les clés étrangères)
    pull_cycle(base_url)
    pull_classe(base_url)
    pull_matiere(base_url)
    pull_annee_scolaire(base_url)
    pull_enseignant(base_url)
    pull_utilisateurs(base_url)
    pull_tarifs(base_url)
    pull_programme(base_url)

    # Puis les tables d'action (recoupement des uuid_client)
    pull_eleve(base_url)
    pull_inscription(base_url)
    pull_paiement(base_url)
    pull_note(base_url)
    pull_presences(base_url)

    print("[PULL] Rafraîchissement terminé.")


# Alias pour compatibilité avec sync_engine.py
synchroniser_toutes_les_donnees = synchroniser_tout_depuis_mysql