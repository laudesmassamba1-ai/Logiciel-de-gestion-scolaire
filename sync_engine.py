import json
import os
import time
import requests
from database import get_connection

# Chemin vers le fichier de configuration
CONFIG_FILE = "config.json"

def charger_configuration():
    """Charge la configuration depuis le fichier JSON ou utilise des valeurs par défaut."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                ip = config.get("server_ip", "127.0.0.1")
                port = config.get("port", 8000)
                return f"http://{ip}:{port}"
        except Exception as e:
            print(f"[ERREUR CONFIG] Impossible de lire le fichier config.json : {e}")
    
    # Valeur de secours par défaut si le fichier n'existe pas
    return "http://127.0.0.1:8000"

# Initialisation de l'URL du serveur
BASE_URL_SERVEUR = charger_configuration()
TIMEOUT = 5  # secondes

print(f"[SYNC ENGINE] Moteur de synchronisation démarré...")
print(f"[SYNC ENGINE] Connecté au serveur cible : {BASE_URL_SERVEUR}")

# --- Le reste de ton code de synchronisation continue ici ---


def tester_connexion() -> bool:
    """Vérifie si le serveur distant est accessible (endpoint /ping)."""
    try:
        response = requests.get(f"{BASE_URL_SERVEUR}/ping", timeout=TIMEOUT)
        return response.status_code == 200
    except Exception:
        return False


def traiter_file_synchro():
    """Parcourt la file d'attente et envoie les requêtes au serveur central."""
    if not tester_connexion():
        return

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, endpoint, methode, payload_json, uuid_client
        FROM file_attente_synchro
        ORDER BY id ASC
    """)
    actions = cursor.fetchall()

    if not actions:
        connection.close()
        return

    print(f"[SYNC] Connection active. {len(actions)} action(s) à synchroniser...")

    for action in actions:
        action_id, endpoint, methode, payload_json, uuid_client = action
        url = f"{BASE_URL_SERVEUR}{endpoint}"
        payload = json.loads(payload_json) if payload_json else {}

        try:
            if methode == "POST":
                res = requests.post(url, json=payload, timeout=TIMEOUT)
            elif methode == "PUT":
                res = requests.put(url, json=payload, timeout=TIMEOUT)
            elif methode == "DELETE":
                res = requests.delete(url, json=payload, timeout=TIMEOUT)
            else:
                continue

            # Succès (200, 201, 204)
            if res.status_code in [200, 201, 204]:
                cursor.execute("DELETE FROM file_attente_synchro WHERE id = ?", (action_id,))
                connection.commit()
                print(f"[SYNC OK] {methode} {endpoint} synchronisé avec succès.")
            else:
                print(f"[SYNC ERREUR] {methode} {endpoint} -> Code HTTP {res.status_code}: {res.text}")
                # On stoppe la boucle pour préserver l'ordre chronologique des requêtes
                break

        except Exception as e:
            print(f"[SYNC ÉCHEC] Impossible de joindre le serveur pour l'action {action_id}: {e}")
            break

    connection.close()


def demarrer_moteur_synchro(intervalle: int = 10):
    """Boucle infinie pour vérifier et exécuter la synchronisation périodiquement."""
    print("[SYNC ENGINE] Moteur de synchronisation démarré...")
    while True:
        try:
            traiter_file_synchro()
        except Exception as e:
            print(f"[SYNC ENGINE] Erreur inattendue : {e}")
        time.sleep(intervalle)


if __name__ == "__main__":
    demarrer_moteur_synchro()