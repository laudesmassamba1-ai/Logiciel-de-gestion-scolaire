import uuid
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
        # Génère un uuid_client stable si absent
        uuid_client = eleve["uuid_client"] if eleve and eleve["uuid_client"] else str(uuid.uuid4())
        if eleve and not eleve["uuid_client"]:
            db.execute("UPDATE eleves SET uuid_client = ? WHERE id = ?", (uuid_client, eleve_id))
        payload = {"eleve_id": eleve_id, "classe_id": classe_id,
                   "date": date, "statut": statut, "motif": motif,
                   "eleve_uuid": uuid_client,
                   "classe_nom": classe["nom"] if classe else None,
                   "uuid_client": uuid_client}
        return self._route_write(
            "POST", "/presence", payload,
            db.execute,
            """INSERT INTO presences (eleve_id, classe_id, date, statut, motif, uuid_client)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (eleve_id, date)
               DO UPDATE SET statut = excluded.statut, motif = excluded.motif,
                             uuid_client = excluded.uuid_client""",
            (eleve_id, classe_id, date, statut, motif, uuid_client))

    def delete_presence(self, presence_id):
        row = db.query_one(
            """SELECT p.uuid_client, e.uuid_client AS eleve_uuid, c.nom AS classe_nom,
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
        else:
            db.execute("DELETE FROM presences WHERE id = ?", (presence_id,))

    def presences_statuts(self):
        return db.query("SELECT statut, COUNT(*) AS total FROM presences GROUP BY statut")

    def all_presences(self):
        return db.query(
            """SELECT p.*, e.matricule, e.nom, e.prenom, c.nom AS classe_nom
               FROM presences p
               JOIN eleves e ON e.id = p.eleve_id
               LEFT JOIN classes c ON c.id = p.classe_id
               ORDER BY p.date DESC""")

    def presences_eleve(self, eleve_id):
        return db.query(
            """SELECT p.*, c.nom AS classe_nom
               FROM presences p LEFT JOIN classes c ON c.id = p.classe_id
               WHERE p.eleve_id = ?
               ORDER BY p.date DESC""", (eleve_id,))
