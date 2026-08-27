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


# ============================================================
# TEST DE CONNEXION
# ============================================================

def tester_connexion() -> bool:
    try:
        response = requests.get(f"{BASE_URL_SERVEUR}/ping", timeout=TIMEOUT)
        return response.status_code == 200
    except Exception:
        return False


# ============================================================
# TRAITEMENT DE LA FILE D'ATTENTE
# ============================================================

def traiter_file_synchro():

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

    print(f"[SYNC] Connexion active. {len(actions)} action(s) à synchroniser...")

    for action_id, endpoint, methode, payload_json, uuid_client in actions:

        url = f"{BASE_URL_SERVEUR}{endpoint}"
        payload = json.loads(payload_json) if payload_json else {}

        try:
            if methode == "POST":
                res = requests.post(url, json=payload, timeout=TIMEOUT)

            elif methode == "PUT":
                res = requests.put(url, json=payload, timeout=TIMEOUT)

            elif methode == "DELETE":
                # Les routes DELETE de l'API n'attendent aucun corps
                res = requests.delete(url, timeout=TIMEOUT)

            else:
                print(f"[SYNC] Méthode inconnue ({methode}), opération {action_id} ignorée.")
                continue

            # Succès
            if res.status_code in (200, 201, 204):
                cursor.execute(
                    "DELETE FROM file_attente_synchro WHERE id = ?", (action_id,)
                )
                connection.commit()
                print(f"[SYNC OK] {methode} {endpoint} synchronisé avec succès.")

            # Payload définitivement invalide : ne bloque pas les autres,
            # mais on la laisse en file pour investigation (pas de perte
            # silencieuse de données).
            elif res.status_code == 422:
                print(f"[SYNC ERREUR 422] {methode} {endpoint} — payload invalide, "
                      f"opération {action_id} laissée en file pour correction.")
                print("Détail :", res.text)
                continue  # on passe à la suivante, pas de blocage global

            # Autre erreur serveur (500, 404...) : on log et on continue,
            # sans bloquer le reste de la file.
            else:
                print(f"[SYNC ERREUR] {methode} {endpoint} -> {res.status_code} : {res.text}")
                continue  # idem, plus de "break" qui bloquait tout

        except requests.exceptions.RequestException as e:
            # Là, c'est vraiment une coupure réseau en plein milieu du
            # traitement : ça, on arrête tout, ça n'a aucun sens de
            # continuer à essayer les suivantes dans la même seconde.
            print(f"[SYNC ÉCHEC] Connexion perdue en cours de synchro : {e}")
            break

    connection.close()


# ============================================================
# BOUCLE PRINCIPALE
# ============================================================

def demarrer_moteur_synchro(intervalle: int = 10):
    print("[SYNC ENGINE] Moteur de synchronisation démarré...")
    print(f"[SYNC ENGINE] Connecté au serveur cible : {BASE_URL_SERVEUR}")
    while True:
        try:
            traiter_file_synchro()
        except Exception as e:
            print(f"[SYNC ENGINE] Erreur inattendue : {e}")
        time.sleep(intervalle)


if __name__ == "__main__":
    initialiser_base()
    demarrer_moteur_synchro()