from urllib.parse import quote

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
        eleve = db.query_one("SELECT uuid_client FROM eleves WHERE id = ?", (eleve_id,))
        classe = db.query_one("SELECT nom FROM classes WHERE id = ?", (classe_id,))
        payload = {"eleve_id": eleve_id, "classe_id": classe_id,
                   "date": date, "statut": statut, "motif": motif,
                   "eleve_uuid": eleve["uuid_client"] if eleve else None,
                   "classe_nom": classe["nom"] if classe else None}
        return self._route_write(
            "POST", "/presence", payload,
            db.execute,
            """INSERT INTO presences (eleve_id, classe_id, date, statut, motif)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (eleve_id, date)
               DO UPDATE SET statut = excluded.statut, motif = excluded.motif""",
            (eleve_id, classe_id, date, statut, motif))

    def delete_presence(self, presence_id):
        row = db.query_one(
            """SELECT e.uuid_client AS uuid_client, c.nom AS classe_nom,
                      p.date, p.statut
               FROM presences p
               JOIN eleves e ON e.id = p.eleve_id
               LEFT JOIN classes c ON c.id = p.classe_id
               WHERE p.id = ?""", (presence_id,))
        if row and row["uuid_client"]:
            ref = "|".join(str(row.get(k) or "")
                           for k in ("uuid_client", "date", "statut", "classe_nom"))
            self._route_write("DELETE", f"/supprimerPresence/{quote(ref)}", {},
                              db.execute, "DELETE FROM presences WHERE id = ?", (presence_id,))

    def presences_statuts(self):
        return db.query("SELECT statut, COUNT(*) AS total FROM presences GROUP BY statut")
