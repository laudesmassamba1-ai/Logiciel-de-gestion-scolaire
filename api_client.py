import requests
from database import get_connection

# Configuration du serveur backend FastAPI
BASE_URL_SERVEUR = "http://localhost:8000"  
TIMEOUT = 3  # Délai maximal (en secondes) avant d'abandonner le réseau et basculer sur SQLite


def recuperer_donnees_hybride(endpoint: str, table_sqlite: str, requete_sqlite: str, params: tuple = ()):
    """
    Fonction centrale de lecture hybride :
    1. Tente de récupérer les données fraîches depuis le serveur distant (GET).
       - Si succès : met à jour le cache local SQLite et renvoie la réponse.
    2. Si le serveur est inaccessible ou hors-ligne :
       - Récupère et renvoie directement les données depuis SQLite local.
    """
    url = f"{BASE_URL_SERVEUR}{endpoint}"

    # 1. Tentative d'accès Réseau (Serveur Central)
    try:
        response = requests.get(url, timeout=TIMEOUT)
        if response.status_code == 200:
            donnees_distantes = response.json()
            # Mise à jour transparente de la base locale SQLite
            sauvegarder_cache_local(table_sqlite, donnees_distantes)
            return {"source": "serveur", "data": donnees_distantes}
    except Exception:
        pass  # Bascule silencieuse sur la base SQLite en cas d'absence d'Internet

    # 2. Mode Secours (SQLite Local)
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(requete_sqlite, params)

    colonnes = [column[0] for column in cursor.description] if cursor.description else []
    lignes = cursor.fetchall()
    donnees_locales = [dict(zip(colonnes, ligne)) for ligne in lignes]
    connection.close()

    return {"source": "local_sqlite", "data": donnees_locales}


def sauvegarder_cache_local(table: str, donnees: list):
    """Met à jour une table SQLite locale avec les données récupérées du serveur."""
    if not isinstance(donnees, list) or len(donnees) == 0:
        return

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(f"DELETE FROM {table}")
        for item in donnees:
            if isinstance(item, dict):
                colonnes = ", ".join(item.keys())
                placeholders = ", ".join(["?"] * len(item))
                valeurs = tuple(item.values())
                cursor.execute(f"INSERT OR REPLACE INTO {table} ({colonnes}) VALUES ({placeholders})", valeurs)
        connection.commit()
    except Exception as e:
        print(f"[CACHE ERREUR] Erreur de synchronisation locale pour {table}: {e}")
    finally:
        connection.close()


# ============================================================
# TOUTES LES FONCTIONS DE LECTURE HYBRIDES (GET)
# ============================================================

# --- 1. Élèves & Inscriptions ---
def obtenir_liste_eleves():
    """GET /eleves - Récupère la liste de tous les élèves"""
    return recuperer_donnees_hybride(
        endpoint="/eleves",
        table_sqlite="eleve",
        requete_sqlite="SELECT * FROM eleve WHERE statut != 'supprime' ORDER BY nom, prenom"
    )

def obtenir_eleve_par_id(eleve_id: int):
    """GET /eleves/{id} - Récupère un élève spécifique par son ID"""
    return recuperer_donnees_hybride(
        endpoint=f"/eleves/{eleve_id}",
        table_sqlite="eleve",
        requete_sqlite="SELECT * FROM eleve WHERE id = ?",
        params=(eleve_id,)
    )

def obtenir_liste_inscriptions():
    """GET /inscriptions - Récupère toutes les inscriptions actives"""
    return recuperer_donnees_hybride(
        endpoint="/inscriptions",
        table_sqlite="inscription",
        requete_sqlite="SELECT * FROM inscription WHERE statut = 'actif'"
    )


# --- 2. Enseignants & Programme ---
def obtenir_liste_enseignants():
    """GET /enseignants - Récupère tous les enseignants"""
    return recuperer_donnees_hybride(
        endpoint="/enseignants",
        table_sqlite="enseignant",
        requete_sqlite="SELECT * FROM enseignant WHERE statut = 'actif' ORDER BY nom, prenom"
    )

def obtenir_programmes_par_classe(classe_id: int):
    """GET /programmes/classe/{classe_id} - Récupère le programme de cours d'une classe"""
    return recuperer_donnees_hybride(
        endpoint=f"/programmes/classe/{classe_id}",
        table_sqlite="programme",
        requete_sqlite="SELECT * FROM programme WHERE classe_id = ?",
        params=(classe_id,)
    )


# --- 3. Finance & Paiements ---
def obtenir_liste_paiements():
    """GET /paiements - Récupère tous les paiements enregistrés"""
    return recuperer_donnees_hybride(
        endpoint="/paiements",
        table_sqlite="paiement",
        requete_sqlite="SELECT * FROM paiement ORDER BY date_paiement DESC"
    )

def obtenir_paiements_par_inscription(inscription_id: int):
    """GET /paiements/inscription/{inscription_id} - Récupère l'historique des paiements d'un élève"""
    return recuperer_donnees_hybride(
        endpoint=f"/paiements/inscription/{inscription_id}",
        table_sqlite="paiement",
        requete_sqlite="SELECT * FROM paiement WHERE inscription_id = ? ORDER BY date_paiement DESC",
        params=(inscription_id,)
    )

def obtenir_tarifs_scolarite():
    """GET /tarifs - Récupère les grilles tarifaires de la scolarité"""
    return recuperer_donnees_hybride(
        endpoint="/tarifs",
        table_sqlite="tarif_scolarite",
        requete_sqlite="SELECT * FROM tarif_scolarite"
    )


# --- 4. Notes & Évaluations ---
def obtenir_notes_par_inscription(inscription_id: int):
    """GET /notes/inscription/{inscription_id} - Récupère le bulletin / les notes d'un élève"""
    return recuperer_donnees_hybride(
        endpoint=f"/notes/inscription/{inscription_id}",
        table_sqlite="note",
        requete_sqlite="SELECT * FROM note WHERE inscription_id = ?",
        params=(inscription_id,)
    )

def obtenir_notes_par_classe_et_matiere(classe_id: int, matiere_id: int, trimestre: str):
    """GET /notes/classe/{classe_id}/matiere/{matiere_id} - Récupère les notes d'une classe pour une matière"""
    return recuperer_donnees_hybride(
        endpoint=f"/notes/classe/{classe_id}/matiere/{matiere_id}?trimestre={trimestre}",
        table_sqlite="note",
        requete_sqlite="SELECT * FROM note WHERE matiere_id = ? AND trimestre = ?",
        params=(matiere_id, trimestre)
    )


# --- 5. Présences & Absences ---
def obtenir_presences_par_classe_et_date(classe_id: int, date_presence: str):
    """GET /presences/classe/{classe_id} - Récupère l'appel du jour pour une classe"""
    return recuperer_donnees_hybride(
        endpoint=f"/presences/classe/{classe_id}?date={date_presence}",
        table_sqlite="presences",
        requete_sqlite="SELECT * FROM presences WHERE classe_id = ? AND date_presence = ?",
        params=(classe_id, date_presence)
    )


# --- 6. Configuration & Structure ---
def obtenir_liste_classes():
    """GET /classes - Récupère toutes les classes"""
    return recuperer_donnees_hybride(
        endpoint="/classes",
        table_sqlite="classe",
        requete_sqlite="SELECT * FROM classe ORDER BY nom"
    )

def obtenir_liste_cycles():
    """GET /cycles - Récupère tous les cycles (Maternelle, Primaire, Collège, Lycée)"""
    return recuperer_donnees_hybride(
        endpoint="/cycles",
        table_sqlite="cycle",
        requete_sqlite="SELECT * FROM cycle"
    )

def obtenir_liste_matieres():
    """GET /matieres - Récupère toutes les matières enregistrées"""
    return recuperer_donnees_hybride(
        endpoint="/matieres",
        table_sqlite="matiere",
        requete_sqlite="SELECT * FROM matiere ORDER BY nom"
    )

def obtenir_annee_scolaire_active():
    """GET /annees-scolaires/active - Récupère l'année scolaire en cours"""
    return recuperer_donnees_hybride(
        endpoint="/annees-scolaires/active",
        table_sqlite="annee_scolaire",
        requete_sqlite="SELECT * FROM annee_scolaire WHERE statut = 'actif' LIMIT 1"
    )


# --- 7. Utilisateurs & Comptes ---
def obtenir_liste_utilisateurs():
    """GET /utilisateurs - Récupère la liste des utilisateurs du système"""
    return recuperer_donnees_hybride(
        endpoint="/utilisateurs",
        table_sqlite="utilisateurs",
        requete_sqlite="SELECT id, nom_utilisateur, role FROM utilisateurs"
    )