
import uuid

from database import db
from repositories.base import RepositoryBase


class PlanningRepository(RepositoryBase):

    def planning_for(self, classe_id):

        rows = db.query(
            "SELECT * FROM planning WHERE classe_id = ?", (classe_id,))
        return {(r["jour"], r["creneau"]): r for r in rows}

    def save_planning(self, classe_id, entries):
        classe = db.query_one("SELECT nom FROM classes WHERE id = ?", (classe_id,))
        classe_nom = classe["nom"] if classe else None
        # Ecriture locale atomique : DELETE + INSERT dans la meme transaction.
        # Si un INSERT echoue, rien n'est supprime -> jamais de planning vide.
        lignes = [(classe_id, jour, creneau, matiere, salle)
                  for jour, creneau, matiere, salle in entries]
        with db.transaction() as txn:
            txn.execute("DELETE FROM planning WHERE classe_id = ?", (classe_id,))
            for ligne in lignes:
                uuid_client = str(uuid.uuid4())
                txn.execute(
                    """INSERT INTO planning (classe_id, jour, creneau, matiere, salle, uuid_client)
                       VALUES (?, ?, ?, ?, ?, ?)""", (*ligne, uuid_client))
        # Push serveur apres commit local reussi : on remplace l'ancien
        # planning de la classe (DELETE) puis on rejoue chaque creneau.
        if classe_nom:
            self._route_write("DELETE", f"/planning/{classe_id}",
                              {"classe_nom": classe_nom},
                              lambda *args, **kwargs: None)
        for jour, creneau, matiere, salle in entries:
            self._route_write(
                "POST", "/planning",
                {"classe_id": classe_id, "jour": jour, "creneau": creneau,
                 "matiere": matiere, "salle": salle, "classe_nom": classe_nom,
                 "uuid_client": str(uuid.uuid4())},
                db.execute,
                "SELECT 1")

    def delete_planning(self, classe_id):
        """Supprime tout le planning d'une classe."""
        classe = db.query_one("SELECT nom FROM classes WHERE id = ?", (classe_id,))
        classe_nom = classe["nom"] if classe else None
        with db.transaction() as txn:
            txn.execute("DELETE FROM planning WHERE classe_id = ?", (classe_id,))
        if classe_nom:
            self._route_write("DELETE", f"/planning/{classe_id}",
                              {"classe_nom": classe_nom},
                              lambda *args, **kwargs: None)
