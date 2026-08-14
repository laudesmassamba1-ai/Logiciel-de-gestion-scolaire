
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

    def save_note(self, eleve_id, matiere_id, periode, devoir1, devoir2, composition):

        payload = {"eleve_id": eleve_id, "matiere_id": matiere_id, "periode": periode,
                   "devoir1": devoir1, "devoir2": devoir2, "composition": composition}
        self._route_write(
            "POST", "/note", payload,
            db.execute,
            """INSERT INTO notes (eleve_id, matiere_id, periode, devoir1, devoir2, composition)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (eleve_id, matiere_id, periode)
               DO UPDATE SET devoir1 = excluded.devoir1, devoir2 = excluded.devoir2,
                             composition = excluded.composition""",
            (eleve_id, matiere_id, periode, devoir1, devoir2, composition))
