import json
import uuid

from database import get_connection


# ============================================================
# AJOUTER UNE OPÉRATION À LA FILE
# ============================================================

def ajouter_a_la_file(endpoint, methode, payload, uuid_client=None):

    connection = get_connection()
    cursor = connection.cursor()

    # Si aucun uuid_client n'est fourni,
    # on en génère un pour l'opération.
    if uuid_client is None:
        uuid_client = str(uuid.uuid4())

    # Conversion du payload en JSON
    payload_json = json.dumps(
        payload,
        ensure_ascii=False
    )

    cursor.execute("""
        INSERT INTO file_attente_synchro (
            endpoint,
            methode,
            payload_json,
            uuid_client
        )
        VALUES (?, ?, ?, ?)
    """, (
        endpoint,
        methode,
        payload_json,
        uuid_client
    ))

    connection.commit()
    connection.close()

    print("Opération ajoutée à la file d'attente.")
    print("UUID client :", uuid_client)


# ============================================================
# PRÉPARER UN ÉLÈVE POUR LA SYNCHRONISATION
# ============================================================

def preparer_eleve_pour_synchro(eleve_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            uuid_client,
            matricule,
            nom,
            prenom,
            sexe,
            date_naissance,
            lieu_naissance,
            adresse,
            nom_parent,
            redoublant,
            statut,
            classe_id,
            telephone_parent
        FROM eleve
        WHERE id = ?
    """, (eleve_id,))

    eleve = cursor.fetchone()

    connection.close()

    if eleve is None:
        raise ValueError(
            f"Aucun élève trouvé avec l'id {eleve_id}"
        )

    (
        uuid_client,
        matricule,
        nom,
        prenom,
        sexe,
        date_naissance,
        lieu_naissance,
        adresse,
        nom_parent,
        redoublant,
        statut,
        classe_id,
        telephone_parent
    ) = eleve

    # ========================================================
    # PAYLOAD EXACTEMENT COMPATIBLE AVEC /eleve
    # ========================================================

    payload = {
        "matricule": matricule,
        "nom": nom,
        "prenom": prenom,
        "sexe": sexe,
        "date_naissance": date_naissance or "",
        "lieu_naissance": lieu_naissance or "",
        "adresse": adresse or "",
        "nom_parent": nom_parent or "",
        "redoublant": redoublant or "0",
        "statut": statut or "",
        "classe_id": classe_id,
        "telephone_parent": telephone_parent or ""
    }

    return uuid_client, payload


# ============================================================
# AJOUTER UN ÉLÈVE À LA FILE DE SYNCHRONISATION
# ============================================================

def ajouter_eleve_a_la_file(eleve_id):

    uuid_client, payload = preparer_eleve_pour_synchro(
        eleve_id
    )

    ajouter_a_la_file(
        endpoint="/eleve",
        methode="POST",
        payload=payload,
        uuid_client=uuid_client
    )

    print(
        f"Élève {eleve_id} préparé pour la synchronisation."
    )


# ============================================================
# LIRE LA FILE D'ATTENTE
# ============================================================

def lire_file_attente():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            endpoint,
            methode,
            payload_json,
            date_creation,
            uuid_client
        FROM file_attente_synchro
        ORDER BY id ASC
    """)

    operations = cursor.fetchall()

    connection.close()

    return operations


# ============================================================
# SUPPRIMER UNE OPÉRATION
# ============================================================

def supprimer_de_la_file(operation_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM file_attente_synchro
        WHERE id = ?
    """, (operation_id,))

    connection.commit()
    connection.close()

    print(
        f"Opération {operation_id} supprimée de la file."
    )


# ============================================================
# TEST DE LA FILE
# ============================================================

if __name__ == "__main__":

    # TEST : ajouter l'élève ID 16 à la file
    ajouter_eleve_a_la_file(16)

    operations = lire_file_attente()

    print("\n===== FILE D'ATTENTE =====")

    if not operations:
        print("Aucune opération en attente.")

    for operation in operations:

        print("\nID :", operation[0])
        print("Endpoint :", operation[1])
        print("Méthode :", operation[2])
        print("Payload :", operation[3])
        print("Date :", operation[4])
        print("UUID client :", operation[5])

    print("\n==========================")