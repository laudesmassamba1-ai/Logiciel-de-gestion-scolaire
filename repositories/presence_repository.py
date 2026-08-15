from database import db
from repositories.base import RepositoryBase


class PresenceRepository(RepositoryBase):

    def presences(self, classe_id, date):
        return db.query(
            """SELECT p.*, e.matricule, e.nom, e.prenom
               FROM presences p JOIN eleves e ON e.id = p.eleve_id
               WHERE e.classe_id = ? AND p.date = ?
               ORDER BY e.nom, e.prenom""", (classe_id, date))

    def save_presence(self, eleve_id, classe_id, date, statut, motif=""):
        payload = {"eleve_id": eleve_id, "classe_id": classe_id,
                   "date": date, "statut": statut, "motif": motif}
        return self._route_write(
            "POST", "/presence", payload,
            db.execute,
            """INSERT INTO presences (eleve_id, classe_id, date, statut, motif)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (eleve_id, date)
               DO UPDATE SET statut = excluded.statut, motif = excluded.motif""",
            (eleve_id, classe_id, date, statut, motif))

    def delete_presence(self, presence_id):
        self._route_write("DELETE", f"/supprimerPresence/{presence_id}", {},
                          db.execute, "DELETE FROM presences WHERE id = ?", (presence_id,))

    def presences_statuts(self):
        return db.query("SELECT statut, COUNT(*) AS total FROM presences GROUP BY statut")
