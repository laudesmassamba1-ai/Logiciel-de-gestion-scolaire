
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
        payload = {"eleve_id": eleve_id, "matiere_id": matiere_id, "periode": periode,
                   "devoir1": devoir1, "devoir2": devoir2, "composition": composition,
                   "eleve_uuid": eleve["uuid_client"] if eleve else None,
                   "matiere_nom": matiere["nom"] if matiere else None}
        self._route_write(
            "POST", "/note", payload,
            db.execute,
            """INSERT INTO notes (eleve_id, matiere_id, periode, devoir1, devoir2, composition)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (eleve_id, matiere_id, periode)
               DO UPDATE SET devoir1 = excluded.devoir1, devoir2 = excluded.devoir2,
                             composition = excluded.composition""",
            (eleve_id, matiere_id, periode, devoir1, devoir2, composition))
