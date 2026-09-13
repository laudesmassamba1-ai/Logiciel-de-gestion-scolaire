
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
        del_payload = {"classe_nom": classe_nom}
        if classe_nom:
            self._route_write("DELETE", f"/planning/{classe_id}", del_payload,
                              db.execute, "DELETE FROM planning WHERE classe_id = ?", (classe_id,))
        # Transaction unique cote local : si un INSERT echoue, rien n'est
        # supprime -> jamais de planning vide en cas d'erreur.
        lignes = [(classe_id, jour, creneau, matiere, salle)
                  for jour, creneau, matiere, salle in entries]
        with db.transaction() as txn:
            txn.execute("DELETE FROM planning WHERE classe_id = ?", (classe_id,))
            for ligne in lignes:
                txn.execute(
                    """INSERT INTO planning (classe_id, jour, creneau, matiere, salle)
                       VALUES (?, ?, ?, ?, ?)""", ligne)
        # Push serveur apres commit local reussi.
        for jour, creneau, matiere, salle in entries:
            self._route_write(
                "POST", "/planning",
                {"classe_id": classe_id, "jour": jour, "creneau": creneau,
                 "matiere": matiere, "salle": salle, "classe_nom": classe_nom},
                db.execute,
                "SELECT 1")
