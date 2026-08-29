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
from database import upsert_reference, remplacer_temp_par_serveur

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


# ============================================================
# TABLES D'ACTION — on rafraîchit ET on marque les lignes
# locales temporaires comme désormais synchronisées (via uuid_client)
# ============================================================

def pull_eleve(base_url):
    data = _get(base_url, "/eleve")
    if not data:
        return
    for e in data.get("eleves", []):
        uuid_client = e.get("uuid_client")
        if uuid_client:
            remplacer_temp_par_serveur("eleve", uuid_client, e["id"])
    print(f"[PULL] Élèves recoupés avec le serveur ({len(data.get('eleves', []))}).")


def pull_paiement(base_url):
    data = _get(base_url, "/paiement")
    if not data:
        return
    for p in data.get("paiement", []):
        uuid_client = p.get("uuid_client")
        if uuid_client:
            remplacer_temp_par_serveur("paiement", uuid_client, p["id"])
    print(f"[PULL] Paiements recoupés avec le serveur ({len(data.get('paiement', []))}).")


def pull_note(base_url):
    data = _get(base_url, "/note")
    if not data:
        return
    for n in data.get("note", []):
        uuid_client = n.get("uuid_client")
        if uuid_client:
            remplacer_temp_par_serveur("note", uuid_client, n["id"])
    print(f"[PULL] Notes recoupées avec le serveur ({len(data.get('note', []))}).")


def pull_presences(base_url):
    # ⚠️ Suppose que ta nouvelle route renvoie {"presences": [...]}
    data = _get(base_url, "/presences")
    if not data:
        return
    for p in data.get("presences", []):
        uuid_client = p.get("uuid_client")
        if uuid_client:
            remplacer_temp_par_serveur("presences", uuid_client, p["id"])
    print(f"[PULL] Présences recoupées avec le serveur ({len(data.get('presences', []))}).")


def pull_inscription(base_url):
    # ⚠️ Suppose que ta nouvelle route renvoie {"inscriptions": [...]}
    data = _get(base_url, "/inscription")
    if not data:
        return
    for i in data.get("inscriptions", []):
        uuid_client = i.get("uuid_client")
        if uuid_client:
            remplacer_temp_par_serveur("inscription", uuid_client, i["id"])
    print(f"[PULL] Inscriptions recoupées avec le serveur ({len(data.get('inscriptions', []))}).")


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

    # Puis les tables d'action (recoupement des uuid_client)
    pull_eleve(base_url)
    pull_inscription(base_url)
    pull_paiement(base_url)
    pull_note(base_url)
    pull_presences(base_url)

    print("[PULL] Rafraîchissement terminé.")


# Alias pour compatibilité avec sync_engine.py
synchroniser_toutes_les_donnees = synchroniser_tout_depuis_mysql
