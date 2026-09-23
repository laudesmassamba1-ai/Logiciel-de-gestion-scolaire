from database import db
from repositories.base import RepositoryBase


class AgendaRepository(RepositoryBase):
    """Calendrier personnel (evenements + alarmes) : table locale sans
    synchronisation serveur, scope par utilisateur."""

    def evenements(self, utilisateur_id):
        return db.query(
            "SELECT * FROM calendrier_evenements WHERE utilisateur_id = ? "
            "ORDER BY jour, heure, id", (utilisateur_id,))

    def evenements_du_jour(self, utilisateur_id, jour):
        return db.query(
            "SELECT * FROM calendrier_evenements "
            "WHERE utilisateur_id = ? AND jour = ? "
            "ORDER BY heure, id", (utilisateur_id, jour))

    def ajouter(self, utilisateur_id, titre, jour, heure, note, alarme):
        return db.execute(
            "INSERT INTO calendrier_evenements "
            "(utilisateur_id, titre, jour, heure, note, alarme) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (utilisateur_id, titre, jour, heure, note, 1 if alarme else 0))

    def modifier(self, evenement_id, titre, jour, heure, note, alarme):
        db.execute(
            "UPDATE calendrier_evenements SET titre = ?, jour = ?, "
            "heure = ?, note = ?, alarme = ?, alarme_signalee = 0 "
            "WHERE id = ?",
            (titre, jour, heure, note, 1 if alarme else 0, evenement_id))

    def supprimer(self, evenement_id):
        db.execute("DELETE FROM calendrier_evenements WHERE id = ?",
                   (evenement_id,))

    def alarmes_dues(self, utilisateur_id):
        """Alarmes non encore signalees dont l'heure est passee (ou egal).

        Fenetre de 365 jours en arriere : si l'app etait fermee au moment
        de l'alarme, elle doit quand meme sonner au prochain demarrage
        (meme apres plusieurs jours). La colonne `alarme_signalee` evite
        les doublons. On filtre quand meme par temps present pour ne pas
        declencher les alarmes futures.
        """
        return db.query(
            "SELECT * FROM calendrier_evenements WHERE utilisateur_id = ? "
            "AND alarme = 1 AND alarme_signalee = 0 "
            "AND (jour || ' ' || COALESCE(heure, '00:00')) <= datetime('now', 'localtime') "
            "AND (jour || ' ' || COALESCE(heure, '00:00')) >= datetime('now', 'localtime', '-365 days') "
            "ORDER BY jour, heure, id", (utilisateur_id,))

    def marquer_alarme_signalee(self, evenement_id):
        db.execute(
            "UPDATE calendrier_evenements SET alarme_signalee = 1 "
            "WHERE id = ?", (evenement_id,))