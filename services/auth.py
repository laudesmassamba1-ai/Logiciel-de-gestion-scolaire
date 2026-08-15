import secrets

from database import db
from database.db import hash_password
from core.config import ROLES

class AuthService:


    def login(self, username, password):

        user = db.query_one(
            "SELECT * FROM utilisateurs WHERE username = ? OR email = ?",
            (username, username))
        if not user:
            return None, "Identifiant ou mot de passe incorrect."
        if not user["actif"]:
            return None, "Ce compte est desactive. Contactez l'administrateur."

        if user["password"] != hash_password(password):
            return None, "Identifiant ou mot de passe incorrect."
        db.execute("UPDATE utilisateurs SET last_login = datetime('now', 'localtime') WHERE id = ?",
                   (user["id"],))
        db.execute("INSERT INTO connexions (utilisateur_id) VALUES (?)", (user["id"],))
        return user, None

    def change_password(self, user_id, old_password, new_password):

        user = db.query_one("SELECT * FROM utilisateurs WHERE id = ?", (user_id,))
        if not user or user["password"] != hash_password(old_password):
            return False, "Ancien mot de passe incorrect."
        db.execute("UPDATE utilisateurs SET password = ? WHERE id = ?",
                   (hash_password(new_password), user_id))
        return True, "Mot de passe mis a jour."

    def random_password(self):

        return secrets.token_hex(6)

    def derniere_connexions(self, limit=20):
        rows = db.query(
            """SELECT u.nom_complet, u.role, c.date_connexion
               FROM connexions c JOIN utilisateurs u ON u.id = c.utilisateur_id
               ORDER BY c.date_connexion DESC LIMIT ?""", (limit,))
        return rows

class RoleAuthorizer:


    NAV = {
        "admin": ["dashboard", "comptes"],
        "directeur": ["dashboard", "stats", "eleves", "classes", "cycles", "notes",
                      "presences", "planning", "caisse", "tarifs", "paiements",
                      "personnel", "programmes", "parametres"],
        "gestionnaire": ["dashboard", "eleves", "classes", "notes", "planning",
                         "caisse", "tarifs", "paiements", "presences"],
    }

    def __init__(self, role):
        self.role = role if role in ROLES else "gestionnaire"

    def allowed(self, page):

        return page in self.NAV.get(self.role, [])

    def can_edit(self, page):
        if page in ("comptes", "parametres"):
            return self.role == "admin"
        return self.role in ("admin", "directeur", "gestionnaire")
