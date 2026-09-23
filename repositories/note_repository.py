
import uuid

from database import db
from repositories.base import RepositoryBase


class NoteRepository(RepositoryBase):

    def notes_for(self, classe_id, matiere_id, periode):

        return db.query(
            """SELECT n.*, e.matricule, e.nom, e.prenom
               FROM notes n JOIN eleves e ON e.id = n.eleve_id
               WHERE e.classe_id = ? AND n.matiere_id = ? AND n.periode = ?
               ORDER BY e.nom, e.prenom""",
            (classe_id, matiere_id, periode))

    def notes_classe(self, classe_id, periode):

        return db.query(
            """SELECT n.*, e.matricule, e.nom, e.prenom,
                      m.nom AS matiere_nom, m.coefficient AS matiere_coeff
               FROM notes n
               JOIN eleves e ON e.id = n.eleve_id
               JOIN matieres m ON m.id = n.matiere_id
               WHERE e.classe_id = ? AND n.periode = ?
               ORDER BY e.nom, e.prenom, m.nom""",
            (classe_id, periode))

    def notes_eleve(self, eleve_id, periode):

        if periode is None:
            return db.query(
                """SELECT n.*, m.nom AS matiere_nom, m.coefficient AS matiere_coeff
                   FROM notes n
                   JOIN matieres m ON m.id = n.matiere_id
                   WHERE n.eleve_id = ?
                   ORDER BY n.periode, m.nom""",
                (eleve_id,))
        return db.query(
            """SELECT n.*, m.nom AS matiere_nom, m.coefficient AS matiere_coeff
               FROM notes n
               JOIN matieres m ON m.id = n.matiere_id
               WHERE n.eleve_id = ? AND n.periode = ?
               ORDER BY m.nom""",
            (eleve_id, periode))

    def save_note(self, eleve_id, matiere_id, periode, devoir1, devoir2, composition):

        eleve = db.query_one("SELECT uuid_client FROM eleves WHERE id = ?", (eleve_id,))
        matiere = db.query_one("SELECT nom FROM matieres WHERE id = ?", (matiere_id,))
        # Génère un uuid_client stable si absent (pour sync idempotente)
        uuid_client = eleve["uuid_client"] if eleve and eleve["uuid_client"] else str(uuid.uuid4())
        if eleve and not eleve["uuid_client"]:
            db.execute("UPDATE eleves SET uuid_client = ? WHERE id = ?", (uuid_client, eleve_id))
        payload = {"eleve_id": eleve_id, "matiere_id": matiere_id, "periode": periode,
                   "devoir1": devoir1, "devoir2": devoir2, "composition": composition,
                   "eleve_uuid": uuid_client,
                   "matiere_nom": matiere["nom"] if matiere else None,
                   "uuid_client": uuid_client}
        self._route_write(
            "POST", "/note", payload,
            db.execute,
            """INSERT INTO notes (eleve_id, matiere_id, periode, devoir1, devoir2, composition, uuid_client)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (eleve_id, matiere_id, periode)
               DO UPDATE SET devoir1 = excluded.devoir1, devoir2 = excluded.devoir2,
                             composition = excluded.composition, uuid_client = excluded.uuid_client""",
            (eleve_id, matiere_id, periode, devoir1, devoir2, composition, uuid_client))

    def delete_note(self, note_id):
        """Supprime une note et propage la suppression via uuid_client."""
        row = db.query_one(
            """SELECT n.uuid_client, e.uuid_client AS eleve_uuid, m.nom AS matiere_nom
               FROM notes n
               JOIN eleves e ON e.id = n.eleve_id
               JOIN matieres m ON m.id = n.matiere_id
               WHERE n.id = ?""", (note_id,))
        if row and row["uuid_client"]:
            from urllib.parse import quote
            self._route_write("DELETE", f"/supprimerNote/{quote(row['uuid_client'])}", {},
                              db.execute, "DELETE FROM notes WHERE id = ?", (note_id,))
        else:
            db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
