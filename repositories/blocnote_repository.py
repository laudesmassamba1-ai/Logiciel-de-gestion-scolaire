from database import db
from repositories.base import RepositoryBase


class BlocNoteRepository(RepositoryBase):
    """Bloc-notes personnel : table locale sans synchronisation serveur
    (comme ia_memoire), scope par utilisateur."""

    def notes(self, utilisateur_id):
        return db.query(
            "SELECT * FROM bloc_notes WHERE utilisateur_id = ? "
            "ORDER BY modifie_le DESC, id DESC", (utilisateur_id,))

    def note(self, note_id):
        return db.query_one(
            "SELECT * FROM bloc_notes WHERE id = ?", (note_id,))

    def ajouter(self, utilisateur_id, titre, contenu):
        return db.execute(
            "INSERT INTO bloc_notes (utilisateur_id, titre, contenu) "
            "VALUES (?, ?, ?)", (utilisateur_id, titre, contenu))

    def modifier(self, note_id, titre, contenu):
        db.execute(
            "UPDATE bloc_notes SET titre = ?, contenu = ?, "
            "modifie_le = datetime('now', 'localtime') WHERE id = ?",
            (titre, contenu, note_id))

    def supprimer(self, note_id):
        db.execute("DELETE FROM bloc_notes WHERE id = ?", (note_id,))