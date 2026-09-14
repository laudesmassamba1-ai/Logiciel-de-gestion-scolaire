import json
import uuid

from database import get_connection, enregistrer_eleve_local

# COUCHE GÉNÉRIQUE

def ajouter_a_la_file(endpoint, methode, payload, uuid_client=None):
    connection = get_connection()
    cursor = connection.cursor()

    if uuid_client is None:
        uuid_client = str(uuid.uuid4())

    payload_json = json.dumps(payload, ensure_ascii=False)

    cursor.execute("""
        INSERT INTO file_attente_synchro (endpoint, methode, payload_json, uuid_client)
        VALUES (?, ?, ?, ?)
    """, (endpoint, methode, payload_json, uuid_client))

    connection.commit()
    connection.close()

    print("Opération ajoutée à la file.", endpoint, methode, uuid_client)
    return uuid_client


def lire_file_attente():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT id, endpoint, methode, payload_json, date_creation, uuid_client
        FROM file_attente_synchro ORDER BY id ASC
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

# ÉLÈVES — table d'action avec uuid_client, CRUD complet

def ajouter_eleve_a_la_file(eleve_dict, paiement_dict, classe_id, annee_scolaire_id=None):
    """POST /ajout_eleve"""
    uuid_client = str(uuid.uuid4())

    eleve_dict = dict(eleve_dict)
    eleve_dict["classe_id"] = classe_id
    paiement_dict = dict(paiement_dict)

    payload_complet = {
        "eleve": eleve_dict,
        "paiement": paiement_dict,
        "uuid_client": uuid_client,
    }

    ajouter_a_la_file("/ajout_eleve", "POST", payload_complet, uuid_client)

    # Écriture locale immédiate pour affichage instantané
    enregistrer_eleve_local(uuid_client, eleve_dict, classe_id, annee_scolaire_id)

    print("Élève préparé pour la synchronisation.")
    return uuid_client


def modifier_eleve_a_la_file(eleve_id_serveur, champs_modifies):
    """PUT /eleve/{eleve_id}"""
    uuid_client = str(uuid.uuid4())
    ajouter_a_la_file(f"/eleve/{eleve_id_serveur}", "PUT", champs_modifies, uuid_client)
    print(f"Modification de l'élève {eleve_id_serveur} mise en file.")
    return uuid_client


def supprimer_eleve_a_la_file(eleve_id_serveur):
    """DELETE /eleve/{id}"""
    uuid_client = str(uuid.uuid4())
    ajouter_a_la_file(f"/eleve/{eleve_id_serveur}", "DELETE", {}, uuid_client)
    print(f"Suppression de l'élève {eleve_id_serveur} mise en file.")
    return uuid_client

# PAIEMENTS — table d'action avec uuid_client, CRUD complet

def ajouter_paiement_a_la_file(inscription_id, type_frais, montant, mode_paiement,
                                 trimestre=None, mois=None):
    """POST /ajout_paiement"""
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
    ajouter_a_la_file("/ajout_paiement", "POST", payload, uuid_client)
    print("Paiement préparé pour la synchronisation.")
    return uuid_client


def modifier_paiement_a_la_file(paiement_id_serveur, champs_modifies):
    """PUT /modifierPaiement/{id}"""
    uuid_client = str(uuid.uuid4())
    ajouter_a_la_file(f"/modifierPaiement/{paiement_id_serveur}", "PUT", champs_modifies, uuid_client)
    print(f"Modification du paiement {paiement_id_serveur} mise en file.")
    return uuid_client


def supprimer_paiement_a_la_file(paiement_id_serveur):
    """DELETE /supprimerPaiement/{id}"""
    uuid_client = str(uuid.uuid4())
    ajouter_a_la_file(f"/supprimerPaiement/{paiement_id_serveur}", "DELETE", {}, uuid_client)
    print(f"Suppression du paiement {paiement_id_serveur} mise en file.")
    return uuid_client

# PRÉSENCES — table d'action avec uuid_client, CRUD complet

def ajouter_presence_a_la_file(eleve_id, statut, classe_id, justifie=None):
    """POST /ajout_presence"""
    uuid_client = str(uuid.uuid4())
    payload = {
        "eleve_id": eleve_id,
        "statut": statut,
        "justifie": justifie,
        "classe_id": classe_id,
        "uuid_client": uuid_client,
    }
    ajouter_a_la_file("/ajout_presence", "POST", payload, uuid_client)
    print("Présence préparée pour la synchronisation.")
    return uuid_client


def modifier_presence_a_la_file(presence_id_serveur, champs_modifies):
    """PUT /modifierPresence/{id}"""
    uuid_client = str(uuid.uuid4())
    ajouter_a_la_file(f"/modifierPresence/{presence_id_serveur}", "PUT", champs_modifies, uuid_client)
    print(f"Modification de la présence {presence_id_serveur} mise en file.")
    return uuid_client


def supprimer_presence_a_la_file(presence_id_serveur):
    """DELETE /supprimerPresence/{id}"""
    uuid_client = str(uuid.uuid4())
    ajouter_a_la_file(f"/supprimerPresence/{presence_id_serveur}", "DELETE", {}, uuid_client)
    print(f"Suppression de la présence {presence_id_serveur} mise en file.")
    return uuid_client

# NOTES — table d'action avec uuid_client, CRUD complet

def ajouter_note_a_la_file(inscription_id, matiere_id, type_evaluation, note,
                             note_sur, date_evaluation, trimestre):
    """POST /ajout_note"""
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
    ajouter_a_la_file("/ajout_note", "POST", payload, uuid_client)
    print("Note préparée pour la synchronisation.")
    return uuid_client


def modifier_note_a_la_file(note_id_serveur, champs_modifies):
    """PUT /modifierNote/{id}"""
    uuid_client = str(uuid.uuid4())
    ajouter_a_la_file(f"/modifierNote/{note_id_serveur}", "PUT", champs_modifies, uuid_client)
    print(f"Modification de la note {note_id_serveur} mise en file.")
    return uuid_client


def supprimer_note_a_la_file(note_id_serveur):
    """DELETE /supprimerNote/{id}"""
    uuid_client = str(uuid.uuid4())
    ajouter_a_la_file(f"/supprimerNote/{note_id_serveur}", "DELETE", {}, uuid_client)
    print(f"Suppression de la note {note_id_serveur} mise en file.")
    return uuid_client

# TEST MANUEL

if __name__ == "__main__":
    ajouter_eleve_a_la_file(
        eleve_dict={
            "matricule": "MAT-TEST-001",
            "nom": "TEST", "prenom": "Hors-ligne",
            "sexe": "M", "date_naissance": "2015-01-01", "lieu_naissance": "Brazzaville",
            "adresse": "Test", "nom_parent": "Parent Test", "redoublant": "0",
            "statut": "actif", "telephone_parent": "060000000",
        },
        paiement_dict={"type_frais": "Inscription", "montant": 15000, "mode_paiement": "espece"},
        classe_id=1,
    )

    for operation in lire_file_attente():
        print(operation)