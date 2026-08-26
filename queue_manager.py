import json
import uuid
from database import get_connection

# ============================================================
# FONCTION GÉNÉRIQUE D'EMPILAGE
# ============================================================

def empiler_action(endpoint: str, methode: str, payload: dict, uuid_client: str = ""):
    """
    Ajoute une requête dans la file d'attente de synchronisation SQLite.
    """
    connection = get_connection()
    cursor = connection.cursor()

    payload_json = json.dumps(payload, ensure_ascii=False) if payload else "{}"

    cursor.execute("""
        INSERT INTO file_attente_synchro (endpoint, methode, payload_json, uuid_client)
        VALUES (?, ?, ?, ?)
    """, (endpoint, methode.upper(), payload_json, uuid_client))

    connection.commit()
    connection.close()
    print(f"[FILE SYNCHRO] Action empilée : {methode.upper()} {endpoint} (UUID/ID: {uuid_client})")


# ============================================================
# 1. ÉLÈVES (POST, PUT, DELETE, RESTAURER)
# ============================================================

def ajouter_eleve_complet_local(donnees_eleve: dict, donnees_paiement: dict, annee_scolaire_id: int) -> str:
    """POST /ajout_eleve (Élève + Inscription + Paiement initial)"""
    connection = get_connection()
    cursor = connection.cursor()

    uuid_eleve = str(uuid.uuid4())
    uuid_inscription = str(uuid.uuid4())
    uuid_paiement = str(uuid.uuid4())

    donnees_eleve["uuid_client"] = uuid_eleve
    donnees_paiement["uuid_client"] = uuid_paiement

    cursor.execute("""
        INSERT INTO eleve (
            nom, prenom, sexe, date_naissance, lieu_naissance,
            adresse, nom_parent, numero_parent, redoublant, statut, uuid_client
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        donnees_eleve.get("nom"),
        donnees_eleve.get("prenom"),
        donnees_eleve.get("sexe"),
        donnees_eleve.get("date_naissance"),
        donnees_eleve.get("lieu_naissance"),
        donnees_eleve.get("adresse"),
        donnees_eleve.get("nom_parent"),
        donnees_eleve.get("telephone_parent") or donnees_eleve.get("numero_parent"),
        donnees_eleve.get("redoublant", "0"),
        donnees_eleve.get("statut", "actif"),
        uuid_eleve
    ))
    eleve_id_local = cursor.lastrowid

    cursor.execute("""
        INSERT INTO inscription (
            eleve_id, classe_id, annee_scolaire_id, statut, uuid_client
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        eleve_id_local,
        donnees_eleve.get("classe_id"),
        annee_scolaire_id,
        "actif",
        uuid_inscription
    ))
    inscription_id_local = cursor.lastrowid

    cursor.execute("""
        INSERT INTO paiement (
            inscription_id, type_frais, montant, mode_paiement, trimestre, mois, uuid_client
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        inscription_id_local,
        donnees_paiement.get("type_frais"),
        donnees_paiement.get("montant"),
        donnees_paiement.get("mode_paiement", "espece"),
        donnees_paiement.get("trimestre"),
        donnees_paiement.get("mois"),
        uuid_paiement
    ))

    connection.commit()
    connection.close()

    payload_global = {
        "eleve": donnees_eleve,
        "paiement": donnees_paiement,
        "uuid_client": uuid_eleve
    }

    empiler_action(endpoint="/ajout_eleve", methode="POST", payload=payload_global, uuid_client=uuid_eleve)
    return uuid_eleve


def modifier_eleve_local(eleve_id: str, nouvelles_donnees: dict) -> bool:
    """PUT /eleve/{eleve_id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE eleve
        SET nom = ?, prenom = ?, sexe = ?, date_naissance = ?, lieu_naissance = ?,
            adresse = ?, nom_parent = ?, numero_parent = ?, redoublant = ?, statut = ?
        WHERE uuid_client = ? OR id = ?
    """, (
        nouvelles_donnees.get("nom"),
        nouvelles_donnees.get("prenom"),
        nouvelles_donnees.get("sexe"),
        nouvelles_donnees.get("date_naissance"),
        nouvelles_donnees.get("lieu_naissance"),
        nouvelles_donnees.get("adresse"),
        nouvelles_donnees.get("nom_parent"),
        nouvelles_donnees.get("telephone_parent") or nouvelles_donnees.get("numero_parent"),
        nouvelles_donnees.get("redoublant", "0"),
        nouvelles_donnees.get("statut", "actif"),
        eleve_id, eleve_id
    ))

    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/eleve/{eleve_id}", methode="PUT", payload=nouvelles_donnees, uuid_client=eleve_id)

    return modifie


def supprimer_eleve_local(eleve_id: str) -> bool:
    """DELETE /eleve/{id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("UPDATE eleve SET statut = 'supprime' WHERE uuid_client = ? OR id = ?", (eleve_id, eleve_id))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/eleve/{eleve_id}", methode="DELETE", payload={}, uuid_client=eleve_id)

    return modifie


def restaurer_eleve_local(nom: str, prenom: str) -> bool:
    """PUT /restaurer_eleve/{nom}/{prenom}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("UPDATE eleve SET statut = 'actif' WHERE nom = ? AND prenom = ?", (nom, prenom))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/restaurer_eleve/{nom}/{prenom}", methode="PUT", payload={})

    return modifie


# ============================================================
# 2. ENSEIGNANTS (POST, PUT, DELETE)
# ============================================================

def ajouter_enseignant_local(donnees: dict) -> int:
    """POST /ajout_enseignant"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO enseignant (
            nom, prenom, sexe, date_naissance, lieu_naissance,
            adresse, telephone, email, diplome, date_embauche, statut
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        donnees.get("nom"), donnees.get("prenom"), donnees.get("sexe"),
        donnees.get("date_naissance"), donnees.get("lieu_naissance"),
        donnees.get("adresse"), donnees.get("telephone"), donnees.get("email"),
        donnees.get("diplome"), donnees.get("date_embauche"), donnees.get("statut", "actif")
    ))
    enseignant_id = cursor.lastrowid
    connection.commit()
    connection.close()

    empiler_action(endpoint="/ajout_enseignant", methode="POST", payload=donnees)
    return enseignant_id


def modifier_enseignant_local(enseignant_id: int, donnees: dict) -> bool:
    """PUT /modifierEnseignant/{id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE enseignant
        SET nom = ?, prenom = ?, sexe = ?, adresse = ?, telephone = ?, email = ?, diplome = ?, statut = ?
        WHERE id = ?
    """, (
        donnees.get("nom"), donnees.get("prenom"), donnees.get("sexe"),
        donnees.get("adresse"), donnees.get("telephone"), donnees.get("email"),
        donnees.get("diplome"), donnees.get("statut", "actif"), enseignant_id
    ))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/modifierEnseignant/{enseignant_id}", methode="PUT", payload=donnees)

    return modifie


def supprimer_enseignant_local(nom: str, prenom: str) -> bool:
    """DELETE /supprimerEnseignant/{nom}/{prenom}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM enseignant WHERE nom = ? AND prenom = ?", (nom, prenom))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/supprimerEnseignant/{nom}/{prenom}", methode="DELETE", payload={})

    return modifie


# ============================================================
# 3. PAIEMENTS (POST, PUT, DELETE)
# ============================================================

def ajouter_paiement_local(donnees: dict) -> str:
    """POST /ajout_paiement"""
    connection = get_connection()
    cursor = connection.cursor()

    nouvel_uuid = str(uuid.uuid4())
    donnees["uuid_client"] = nouvel_uuid

    cursor.execute("""
        INSERT INTO paiement (
            inscription_id, type_frais, montant, mode_paiement, trimestre, mois, uuid_client
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        donnees.get("inscription_id"), donnees.get("type_frais"), donnees.get("montant"),
        donnees.get("mode_paiement", "espece"), donnees.get("trimestre"), donnees.get("mois"), nouvel_uuid
    ))

    connection.commit()
    connection.close()

    empiler_action(endpoint="/ajout_paiement", methode="POST", payload=donnees, uuid_client=nouvel_uuid)
    return nouvel_uuid


def modifier_paiement_local(paiement_id: str, donnees: dict) -> bool:
    """PUT /modifierPaiement/{id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE paiement
        SET type_frais = ?, montant = ?, mode_paiement = ?, trimestre = ?, mois = ?
        WHERE uuid_client = ? OR id = ?
    """, (
        donnees.get("type_frais"), donnees.get("montant"),
        donnees.get("mode_paiement"), donnees.get("trimestre"), donnees.get("mois"),
        paiement_id, paiement_id
    ))

    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/modifierPaiement/{paiement_id}", methode="PUT", payload=donnees, uuid_client=paiement_id)

    return modifie


def supprimer_paiement_local(paiement_id: str) -> bool:
    """DELETE /supprimerPaiement/{id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM paiement WHERE uuid_client = ? OR id = ?", (paiement_id, paiement_id))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/supprimerPaiement/{paiement_id}", methode="DELETE", payload={}, uuid_client=paiement_id)

    return modifie


# ============================================================
# 4. NOTES (POST, PUT, DELETE)
# ============================================================

def ajouter_note_local(donnees: dict) -> str:
    """POST /ajout_note"""
    connection = get_connection()
    cursor = connection.cursor()

    nouvel_uuid = str(uuid.uuid4())
    donnees["uuid_client"] = nouvel_uuid

    cursor.execute("""
        INSERT INTO note (
            inscription_id, matiere_id, type_evaluation, note, note_sur,
            date_evaluation, trimestre, uuid_client
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        donnees.get("inscription_id"), donnees.get("matiere_id"),
        donnees.get("type_evaluation", "Devoir"), donnees.get("note"),
        donnees.get("note_sur", 20), donnees.get("date_evaluation"),
        donnees.get("trimestre"), nouvel_uuid
    ))

    connection.commit()
    connection.close()

    empiler_action(endpoint="/ajout_note", methode="POST", payload=donnees, uuid_client=nouvel_uuid)
    return nouvel_uuid


def modifier_note_local(note_id: str, donnees: dict) -> bool:
    """PUT /modifierNote/{id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE note
        SET note = ?, note_sur = ?, type_evaluation = ?, date_evaluation = ?, trimestre = ?
        WHERE uuid_client = ? OR id = ?
    """, (
        donnees.get("note"), donnees.get("note_sur", 20), donnees.get("type_evaluation"),
        donnees.get("date_evaluation"), donnees.get("trimestre"), note_id, note_id
    ))

    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/modifierNote/{note_id}", methode="PUT", payload=donnees, uuid_client=note_id)

    return modifie


def supprimer_note_local(note_id: str) -> bool:
    """DELETE /supprimerNote/{id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM note WHERE uuid_client = ? OR id = ?", (note_id, note_id))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/supprimerNote/{note_id}", methode="DELETE", payload={}, uuid_client=note_id)

    return modifie


# ============================================================
# 5. PRÉSENCES (POST, PUT, DELETE)
# ============================================================

def enregistrer_presence_local(donnees: dict) -> str:
    """POST /ajout_presence"""
    connection = get_connection()
    cursor = connection.cursor()

    nouvel_uuid = str(uuid.uuid4())
    donnees["uuid_client"] = nouvel_uuid

    cursor.execute("""
        INSERT INTO presences (
            eleve_id, classe_id, date_presence, statut, justifie, uuid_client
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        donnees.get("eleve_id"), donnees.get("classe_id"), donnees.get("date_presence"),
        donnees.get("statut", "Present"), donnees.get("justifie", "Non"), nouvel_uuid
    ))

    connection.commit()
    connection.close()

    empiler_action(endpoint="/ajout_presence", methode="POST", payload=donnees, uuid_client=nouvel_uuid)
    return nouvel_uuid


def modifier_presence_local(presence_id: str, donnees: dict) -> bool:
    """PUT /modifierPresence/{id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE presences
        SET statut = ?, justifie = ?
        WHERE uuid_client = ? OR id = ?
    """, (
        donnees.get("statut"), donnees.get("justifie", "Non"), presence_id, presence_id
    ))

    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/modifierPresence/{presence_id}", methode="PUT", payload=donnees, uuid_client=presence_id)

    return modifie


def supprimer_presence_local(presence_id: str) -> bool:
    """DELETE /supprimerPresence/{id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM presences WHERE uuid_client = ? OR id = ?", (presence_id, presence_id))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/supprimerPresence/{presence_id}", methode="DELETE", payload={}, uuid_client=presence_id)

    return modifie


# ============================================================
# 6. CLASSES & CYCLES (POST, PUT, DELETE)
# ============================================================

def ajouter_classe_local(donnees: dict) -> int:
    """POST /ajout_classe"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("INSERT INTO classe (nom, cycle_id) VALUES (?, ?)", (donnees.get("nom"), donnees.get("cycle_id")))
    classe_id = cursor.lastrowid
    connection.commit()
    connection.close()

    empiler_action(endpoint="/ajout_classe", methode="POST", payload=donnees)
    return classe_id


def modifier_classe_local(classe_id: int, donnees: dict) -> bool:
    """PUT /classe/{classe_id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("UPDATE classe SET nom = ?, cycle_id = ? WHERE id = ?", (donnees.get("nom"), donnees.get("cycle_id"), classe_id))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/classe/{classe_id}", methode="PUT", payload=donnees)

    return modifie


def supprimer_classe_local(nom_classe: str) -> bool:
    """DELETE /supprimerClasse/{classe}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM classe WHERE nom = ?", (nom_classe,))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/supprimerClasse/{nom_classe}", methode="DELETE", payload={})

    return modifie


def ajouter_cycle_local(donnees: dict) -> int:
    """POST /ajout_cycle"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("INSERT INTO cycle (nom) VALUES (?)", (donnees.get("nom"),))
    cycle_id = cursor.lastrowid
    connection.commit()
    connection.close()

    empiler_action(endpoint="/ajout_cycle", methode="POST", payload=donnees)
    return cycle_id


def modifier_cycle_local(cycle_id: int, donnees: dict) -> bool:
    """PUT /modifierCycle/{cycle_id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("UPDATE cycle SET nom = ? WHERE id = ?", (donnees.get("nom"), cycle_id))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/modifierCycle/{cycle_id}", methode="PUT", payload=donnees)

    return modifie


def supprimer_cycle_local(cycle_id: int) -> bool:
    """DELETE /supprimerCycle/{id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM cycle WHERE id = ?", (cycle_id,))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/supprimerCycle/{cycle_id}", methode="DELETE", payload={})

    return modifie


# ============================================================
# 7. MATIÈRES & PROGRAMMES (POST, PUT, DELETE)
# ============================================================

def ajouter_matiere_local(donnees: dict) -> int:
    """POST /ajout_matiere"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("INSERT INTO matiere (nom, code) VALUES (?, ?)", (donnees.get("nom"), donnees.get("code")))
    matiere_id = cursor.lastrowid
    connection.commit()
    connection.close()

    empiler_action(endpoint="/ajout_matiere", methode="POST", payload=donnees)
    return matiere_id


def modifier_matiere_local(matiere_id: int, donnees: dict) -> bool:
    """PUT /modifierMatiere/{id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("UPDATE matiere SET nom = ?, code = ? WHERE id = ?", (donnees.get("nom"), donnees.get("code"), matiere_id))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/modifierMatiere/{matiere_id}", methode="PUT", payload=donnees)

    return modifie


def supprimer_matiere_local(matiere_id: int) -> bool:
    """DELETE /supprimerMatiere/{id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM matiere WHERE id = ?", (matiere_id,))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/supprimerMatiere/{matiere_id}", methode="DELETE", payload={})

    return modifie


def associer_matiere_classe_enseignant_local(donnees: dict) -> int:
    """POST /associerMatiereClasseEnseignant"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO programme (classe_id, matiere_id, enseignant_id, coefficient)
        VALUES (?, ?, ?, ?)
    """, (
        donnees.get("classe_id"), donnees.get("matiere_id"),
        donnees.get("enseignant_id"), donnees.get("coefficient", 1)
    ))
    programme_id = cursor.lastrowid
    connection.commit()
    connection.close()

    empiler_action(endpoint="/associerMatiereClasseEnseignant", methode="POST", payload=donnees)
    return programme_id


def modifier_programme_local(programme_id: int, donnees: dict) -> bool:
    """PUT /modifierProgramme/{id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE programme
        SET classe_id = ?, matiere_id = ?, enseignant_id = ?, coefficient = ?
        WHERE id = ?
    """, (
        donnees.get("classe_id"), donnees.get("matiere_id"),
        donnees.get("enseignant_id"), donnees.get("coefficient", 1), programme_id
    ))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/modifierProgramme/{programme_id}", methode="PUT", payload=donnees)

    return modifie


def supprimer_programme_local(programme_id: int) -> bool:
    """DELETE /supprimerProgramme/{id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM programme WHERE id = ?", (programme_id,))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/supprimerProgramme/{programme_id}", methode="DELETE", payload={})

    return modifie


# ============================================================
# 8. ANNÉES SCOLAIRES & TARIFS (POST, PUT, DELETE)
# ============================================================

def ajouter_annee_scolaire_local(donnees: dict) -> int:
    """POST /ajouter_annee_scolaire"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO annee_scolaire (libelle, date_debut, date_fin, statut)
        VALUES (?, ?, ?, ?)
    """, (
        donnees.get("libelle"), donnees.get("date_debut"),
        donnees.get("date_fin"), donnees.get("statut", "actif")
    ))
    annee_id = cursor.lastrowid
    connection.commit()
    connection.close()

    empiler_action(endpoint="/ajouter_annee_scolaire", methode="POST", payload=donnees)
    return annee_id


def ajouter_tarif_scolarite_local(donnees: dict) -> int:
    """POST /ajout_tarifs-scolarite"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO tarif_scolarite (cycle_id, type_frais, montant, annee_scolaire_id)
        VALUES (?, ?, ?, ?)
    """, (
        donnees.get("cycle_id"), donnees.get("type_frais"),
        donnees.get("montant"), donnees.get("annee_scolaire_id")
    ))
    tarif_id = cursor.lastrowid
    connection.commit()
    connection.close()

    empiler_action(endpoint="/ajout_tarifs-scolarite", methode="POST", payload=donnees)
    return tarif_id


def modifier_tarif_scolarite_local(tarif_id: int, donnees: dict) -> bool:
    """PUT /tarifs-scolarite/{tarif_id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE tarif_scolarite
        SET cycle_id = ?, type_frais = ?, montant = ?
        WHERE id = ?
    """, (
        donnees.get("cycle_id"), donnees.get("type_frais"),
        donnees.get("montant"), tarif_id
    ))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/tarifs-scolarite/{tarif_id}", methode="PUT", payload=donnees)

    return modifie


def supprimer_tarif_scolarite_local(tarif_id: int) -> bool:
    """DELETE /tarifs-scolarite/{tarif_id}"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM tarif_scolarite WHERE id = ?", (tarif_id,))
    modifie = cursor.rowcount > 0
    connection.commit()
    connection.close()

    if modifie:
        empiler_action(endpoint=f"/tarifs-scolarite/{tarif_id}", methode="DELETE", payload={})

    return modifie


# ============================================================
# 9. UTILISATEURS (POST)
# ============================================================

def ajouter_utilisateur_local(donnees: dict) -> int:
    """POST /ajout_utilisateurs"""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO utilisateurs (nom_utilisateur, mot_de_passe_hash, role)
        VALUES (?, ?, ?)
    """, (
        donnees.get("nom_utilisateur"),
        donnees.get("mot_de_passe"),
        donnees.get("role", "utilisateur")
    ))
    user_id = cursor.lastrowid
    connection.commit()
    connection.close()

    empiler_action(endpoint="/ajout_utilisateurs", methode="POST", payload=donnees)
    return user_id