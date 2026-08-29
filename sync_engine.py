import json
import os
import time
import requests

from database import get_connection, initialiser_base


# ============================================================
# CONFIGURATION SERVEUR (via config.json)
# ============================================================

CONFIG_FILE = "config.json"


def charger_configuration():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                ip = config.get("server_ip", "127.0.0.1")
                port = config.get("port", 8000)
                return f"http://{ip}:{port}"
        except Exception as e:
            print(f"[ERREUR CONFIG] Impossible de lire config.json : {e}")
    return "http://127.0.0.1:8000"


BASE_URL_SERVEUR = charger_configuration()
TIMEOUT = 5


def tester_connexion() -> bool:
    try:
        response = requests.get(f"{BASE_URL_SERVEUR}/ping", timeout=TIMEOUT)
        return response.status_code == 200
    except Exception:
        return False


# ============================================================
# 1. PUSH — envoyer la file d'attente locale vers MySQL
# ============================================================

def traiter_file_synchro():

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

    print(f"[SYNC] {len(actions)} action(s) à envoyer vers le serveur...")

    for action_id, endpoint, methode, payload_json, uuid_client in actions:

        url = f"{BASE_URL_SERVEUR}{endpoint}"
        payload = json.loads(payload_json) if payload_json else {}

        try:
            if methode == "POST":
                res = requests.post(url, json=payload, timeout=TIMEOUT)
            elif methode == "PUT":
                res = requests.put(url, json=payload, timeout=TIMEOUT)
            elif methode == "DELETE":
                res = requests.delete(url, timeout=TIMEOUT)
            else:
                print(f"[SYNC] Méthode inconnue ({methode}), opération {action_id} ignorée.")
                continue

            if res.status_code in (200, 201, 204):
                cursor.execute("DELETE FROM file_attente_synchro WHERE id = ?", (action_id,))
                connection.commit()
                print(f"[SYNC OK] {methode} {endpoint} synchronisé avec succès.")

            elif res.status_code == 422:
                print(f"[SYNC ERREUR 422] {methode} {endpoint} — payload invalide, "
                      f"opération {action_id} laissée en file. Détail : {res.text}")
                continue

            else:
                print(f"[SYNC ERREUR] {methode} {endpoint} -> {res.status_code} : {res.text}")
                continue

        except requests.exceptions.RequestException as e:
            print(f"[SYNC ÉCHEC] Connexion perdue en cours de push : {e}")
            break

    connection.close()


# ============================================================
# 2. PULL — rafraîchir le cache local depuis MySQL
# ============================================================

def rafraichir_cache_local():
    try:
        # Import différé pour éviter une boucle d'import avec sync_pull.py
        from sync_pull import synchroniser_tout_depuis_mysql
        synchroniser_tout_depuis_mysql()
    except Exception as e:
        print(f"[PULL] Erreur pendant le rafraîchissement du cache : {e}")


# ============================================================
# CYCLE COMPLET : push puis pull, seulement si en ligne
# ============================================================

def cycle_synchro():
    if not tester_connexion():
        print("[SYNC] Hors ligne — aucune synchro ce cycle.")
        return

    print("[SYNC] En ligne — début du cycle de synchronisation.")
    traiter_file_synchro()      # 1. on envoie ce qui est en attente
    rafraichir_cache_local()    # 2. on rapatrie l'état à jour du serveur
    print("[SYNC] Cycle terminé.")


def demarrer_moteur_synchro(intervalle: int = 10):
    print("[SYNC ENGINE] Moteur de synchronisation démarré...")
    print(f"[SYNC ENGINE] Connecté au serveur cible : {BASE_URL_SERVEUR}")
    while True:
        try:
            cycle_synchro()
        except Exception as e:
            print(f"[SYNC ENGINE] Erreur inattendue : {e}")
        time.sleep(intervalle)


if __name__ == "__main__":
    initialiser_base()
    demarrer_moteur_synchro()
