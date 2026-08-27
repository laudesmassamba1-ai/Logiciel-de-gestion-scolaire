import json
import uuid

from database import get_connection, enregistrer_eleve_local


# ============================================================
# COUCHE GÉNÉRIQUE — sert de base à toutes les fonctions
# spécifiques ci-dessous. Ne pas modifier sauf besoin global.
# ============================================================

def ajouter_a_la_file(endpoint, methode, payload, uuid_client=None):

    connection = get_connection()
    cursor = connection.cursor()

    if uuid_client is None:
        uuid_client = str(uuid.uuid4())

    payload_json = json.dumps(payload, ensure_ascii=False)

    cursor.execute("""
        INSERT INTO file_attente_synchro (
            endpoint, methode, payload_json, uuid_client
        ) VALUES (?, ?, ?, ?)
    """, (endpoint, methode, payload_json, uuid_client))

    connection.commit()
    connection.close()

    print("Opération ajoutée à la file d'attente.")
    print("Endpoint :", endpoint, "| Méthode :", methode, "| UUID :", uuid_client)

    return uuid_client


def lire_file_attente():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT id, endpoint, methode, payload_json, date_creation, uuid_client
        FROM file_attente_synchro
        ORDER BY id ASC
    """)
    operations = cursor.fetchall()
    connection.close()
    return operations


def supprimer_de_la_file(operation_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM file_attente_synchro WHERE id = ?", (operation_id,))
    connection.commit()
    connection.close()
    print(f"Opération {operation_id} supprimée de la file.")


# ============================================================
# ÉLÈVES — inscription (POST /eleve)
# La route réelle attend : { eleve: {...}, paiement: {...}, uuid_client }
# ============================================================

def ajouter_eleve_a_la_file(eleve_dict, paiement_dict):
    """
    eleve_dict : matricule, nom, prenom, sexe, date_naissance, lieu_naissance,
                 adresse, nom_parent, redoublant, statut, classe_id, telephone_parent
    paiement_dict : type_frais, montant, mode_paiement, trimestre (optionnel), mois (optionnel)
    """
    uuid_client = str(uuid.uuid4())

    eleve_dict = dict(eleve_dict)
    paiement_dict = dict(paiement_dict)

    payload_complet = {
        "eleve": eleve_dict,
        "paiement": paiement_dict,
        "uuid_client": uuid_client,
    }

    ajouter_a_la_file(
        endpoint="/eleve",
        methode="POST",
        payload=payload_complet,
        uuid_client=uuid_client,
    )

    # On l'affiche tout de suite dans l'interface, sans attendre la synchro
    enregistrer_eleve_local(uuid_client, eleve_dict)

    print("Élève préparé pour la synchronisation.")
    return uuid_client


# ============================================================
# ÉLÈVES — modification (PUT /eleve/{id})
# L'élève doit déjà exister côté serveur (donc avoir un id réel,
# pas seulement un uuid_client) pour pouvoir être modifié en ligne.
# ============================================================

def modifier_eleve_a_la_file(eleve_id_serveur, champs_modifies):
    """
    eleve_id_serveur : l'id réel côté MySQL (pas l'uuid_client)
    champs_modifies : dict des seuls champs à changer, ex: {"statut": "inactif"}
    """
    uuid_client = str(uuid.uuid4())

    ajouter_a_la_file(
        endpoint=f"/eleve/{eleve_id_serveur}",
        methode="PUT",
        payload=champs_modifies,
        uuid_client=uuid_client,
    )
    print(f"Modification de l'élève {eleve_id_serveur} mise en file.")
    return uuid_client


# ============================================================
# PAIEMENTS — nouveau versement (POST /paiement)
# ============================================================

def ajouter_paiement_a_la_file(inscription_id, type_frais, montant, mode_paiement,
                                 trimestre=None, mois=None):
    uuid_client = str(uuid.uuid4())

    payload = {
        "inscription_id": inscription_id,
        "type_frais": type_frais,
        "montant": montant,
        "mode_paiement": mode_paiement,
        "trimestre": trimestre,
        "mois": mois,
        "uuid_client": uuid_client,
    }

    ajouter_a_la_file(
        endpoint="/paiement",
        methode="POST",
        payload=payload,
        uuid_client=uuid_client,
    )
    print("Paiement préparé pour la synchronisation.")
    return uuid_client


# ============================================================
# PRÉSENCES — appel du jour (POST /presence)
# ============================================================

def ajouter_presence_a_la_file(eleve_id, statut, classe_id, justifie=None):
    """
    statut : "Present", "Absent" ou "En retard"
    justifie : "Oui" / "Non" / None
    """
    uuid_client = str(uuid.uuid4())

    payload = {
        "eleve_id": eleve_id,
        "statut": statut,
        "justifie": justifie,
        "classe_id": classe_id,
        "uuid_client": uuid_client,
    }

    ajouter_a_la_file(
        endpoint="/presence",
        methode="POST",
        payload=payload,
        uuid_client=uuid_client,
    )
    print("Présence préparée pour la synchronisation.")
    return uuid_client


# ============================================================
# NOTES — saisie d'une note (POST /note)
# ============================================================

def ajouter_note_a_la_file(inscription_id, matiere_id, type_evaluation, note,
                             note_sur, date_evaluation, trimestre):
    uuid_client = str(uuid.uuid4())

    payload = {
        "inscription_id": inscription_id,
        "matiere_id": matiere_id,
        "type_evaluation": type_evaluation,
        "note": note,
        "note_sur": note_sur,
        "date_evaluation": date_evaluation,
        "trimestre": trimestre,
        "uuid_client": uuid_client,
    }

    ajouter_a_la_file(
        endpoint="/note",
        methode="POST",
        payload=payload,
        uuid_client=uuid_client,
    )
    print("Note préparée pour la synchronisation.")
    return uuid_client


# ============================================================
# TEST MANUEL
# ============================================================

if __name__ == "__main__":

    # Exemple : inscription d'un élève avec son premier paiement
    ajouter_eleve_a_la_file(
        eleve_dict={
            "matricule": "LOCAL-TEST-01",
            "nom": "TEST",
            "prenom": "Hors-ligne",
            "sexe": "M",
            "date_naissance": "2015-01-01",
            "lieu_naissance": "Brazzaville",
            "adresse": "Test",
            "nom_parent": "Parent Test",
            "redoublant": "0",
            "statut": "actif",
            "classe_id": 8,
            "telephone_parent": "060000000",
        },
        paiement_dict={
            "type_frais": "Inscription",
            "montant": 15000,
            "mode_paiement": "espece",
        },
    )

    operations = lire_file_attente()
    print("\n===== FILE D'ATTENTE =====")
    for operation in operations:
        print("\nID :", operation[0])
        print("Endpoint :", operation[1])
        print("Méthode :", operation[2])
        print("Payload :", operation[3])
        print("UUID client :", operation[5])
    print("\n==========================")