import json
import requests

from sync_queue import (
    lire_file_attente,
    supprimer_de_la_file
)


# ============================================================
# CONFIGURATION API
# ============================================================

API_URL = "http://127.0.0.1:8000"


# ============================================================
# SYNCHRONISATION DE LA FILE
# ============================================================

def synchroniser_file():

    operations = lire_file_attente()

    if not operations:

        print("Aucune opération en attente.")
        return

    print(
        f"{len(operations)} opération(s) à synchroniser."
    )

    for operation in operations:

        operation_id = operation[0]
        endpoint = operation[1]
        methode = operation[2]
        payload_json = operation[3]
        uuid_client = operation[5]

        # Conversion JSON → dictionnaire Python
        payload = json.loads(payload_json)

        # ====================================================
        # CONSTRUCTION DU NOUVEAU PAYLOAD
        # ====================================================

        payload_sync = {
            "uuid_client": uuid_client,
            "eleve": payload
        }

        url = API_URL + endpoint

        print("\n--------------------------")
        print("Synchronisation...")
        print("ID :", operation_id)
        print("UUID client :", uuid_client)
        print("URL :", url)
        print("Méthode :", methode)
        print("Payload :", payload_sync)

        try:

            # =================================================
            # POST
            # =================================================

            if methode == "POST":

                response = requests.post(
                    url,
                    json=payload_sync,
                    timeout=5
                )

            # =================================================
            # PUT
            # =================================================

            elif methode == "PUT":

                response = requests.put(
                    url,
                    json=payload_sync,
                    timeout=5
                )

            # =================================================
            # DELETE
            # =================================================

            elif methode == "DELETE":

                response = requests.delete(
                    url,
                    json=payload_sync,
                    timeout=5
                )

            # =================================================
            # MÉTHODE INCONNUE
            # =================================================

            else:

                print(
                    "Méthode inconnue :",
                    methode
                )

                continue

            # =================================================
            # RÉSULTAT
            # =================================================

            print(
                "Code HTTP :",
                response.status_code
            )

            if response.ok:

                print(
                    "✅ Synchronisation réussie."
                )

                print(
                    "Réponse serveur :",
                    response.text
                )

                supprimer_de_la_file(
                    operation_id
                )

            else:

                print(
                    "❌ Échec de la synchronisation."
                )

                print(
                    "Réponse serveur :",
                    response.text
                )

        except requests.exceptions.RequestException as erreur:

            print(
                "❌ Impossible de contacter le serveur."
            )

            print(
                "Erreur :",
                erreur
            )


# ============================================================
# POINT D'ENTRÉE
# ============================================================

if __name__ == "__main__":

    synchroniser_file()