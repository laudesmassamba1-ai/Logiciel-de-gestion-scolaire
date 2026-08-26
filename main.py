import threading
import time
from database import initialiser_base
from sync_engine import demarrer_moteur_synchro
import api_client
# Importe ton queue_manager pour les opérations POST/PUT/DELETE
import queue_manager 

def lancer_application():
    # 1. Initialiser la base de données locale SQLite
    print("[INIT] Initialisation de la base SQLite locale...")
    initialiser_base()

    # 2. Lancer le moteur de synchronisation en arrière-plan (Thread séparé)
    print("[INIT] Démarrage du thread de synchronisation...")
    thread_synchro = threading.Thread(
        target=demarrer_moteur_synchro, 
        kwargs={"intervalle": 10},  # Vérifie toutes les 10 secondes
        daemon=True  # S'arrête automatiquement quand l'application principale ferme
    )
    thread_synchro.start()

    # 3. Lancement du reste de ton application (Exemple de test)
    print("[APP] Application prête et en cours d'exécution !")
    
    # --- TEST RAPIDE DE FONCTIONNEMENT ---
    # Exemple 1: Lecture d'élèves (hybride)
    res_eleves = api_client.obtenir_liste_eleves()
    print(f"[TEST GET] Source: {res_eleves['source']}, Nb élèves: {len(res_eleves['data'])}")

    # Garder le script principal éveillé (si c'est un script console)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[STOP] Fermeture de l'application.")

if __name__ == "__main__":
    lancer_application()