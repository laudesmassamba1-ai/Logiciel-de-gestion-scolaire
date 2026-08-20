
from database import db
from repositories.base import RepositoryBase


class PlanningRepository(RepositoryBase):

    def planning_for(self, classe_id):

        rows = db.query(
            "SELECT * FROM planning WHERE classe_id = ?", (classe_id,))
        return {(r["jour"], r["creneau"]): r for r in rows}

    def save_planning(self, classe_id, entries):
        self._route_write("DELETE", f"/planning/{classe_id}", {},
                          db.execute, "DELETE FROM planning WHERE classe_id = ?", (classe_id,))
        for jour, creneau, matiere, salle in entries:
            self._route_write(
                "POST", "/planning",
                {"classe_id": classe_id, "jour": jour, "creneau": creneau,
                 "matiere": matiere, "salle": salle},
                db.execute,
                "INSERT INTO planning (classe_id, jour, creneau, matiere, salle) VALUES (?, ?, ?, ?, ?)",
                (classe_id, jour, creneau, matiere, salle))
