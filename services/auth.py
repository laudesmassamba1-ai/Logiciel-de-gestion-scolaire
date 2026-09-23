import secrets

from database import db
from database.db import hash_password, verify_password
from core.config import ROLES


class AuthService:

    def has_accounts(self):
        count = db.query_one("SELECT COUNT(*) AS c FROM utilisateurs")
        return count and count["c"] > 0

    def login(self, username, password):
        user = db.query_one(
            "SELECT * FROM utilisateurs WHERE username = ? OR email = ?",
            (username, username))
        # Message volontairement identique quel que soit le cas : pas de
        # divulgation de l'existence d'un compte ni de son etat (extremite).
        if not user or not verify_password(password, user["password"]) \
                or not user["actif"]:
            return None, "Identifiant ou mot de passe incorrect."
        # Upgrade silencieux : les tres anciens hash SHA-256 non sales sont
        # re-haches en PBKDF2 des que le mot de passe est verifie correct.
        if ":" not in user["password"]:
            db.execute("UPDATE utilisateurs SET password = ? WHERE id = ?",
                       (hash_password(password), user["id"]))
        db.execute("UPDATE utilisateurs SET last_login = datetime('now', 'localtime') WHERE id = ?",
                   (user["id"],))
        db.execute("INSERT INTO connexions (utilisateur_id) VALUES (?)", (user["id"],))
        return user, None

    def get_saved_user(self):
        params = db.query_one(
            "SELECT valeur FROM parametres WHERE cle = 'dernier_utilisateur_id'")
        if params and params["valeur"]:
            user = db.query_one(
                "SELECT * FROM utilisateurs WHERE id = ? AND actif = 1",
                (int(params["valeur"]),))
            if user:
                return user
        return None

    def save_session(self, user_id):
        db.execute(
            "INSERT INTO parametres (cle, valeur) VALUES (?, ?) "
            "ON CONFLICT (cle) DO UPDATE SET valeur = excluded.valeur",
            ("dernier_utilisateur_id", str(user_id)))

    def clear_session(self):
        db.execute(
            "INSERT INTO parametres (cle, valeur) VALUES (?, ?) "
            "ON CONFLICT (cle) DO UPDATE SET valeur = excluded.valeur",
            ("dernier_utilisateur_id", ""))

    def change_password(self, user_id, old_password, new_password):
        user = db.query_one("SELECT * FROM utilisateurs WHERE id = ?", (user_id,))
        if not user or not verify_password(old_password, user["password"]):
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
    """Controle d'acces par role. Principe: tout ce qui n'est pas
    explicitement autorise est interdit (deny by default)."""

    # Pages visibles dans la navigation, par role.
    NAV = {
        "directeur": ["dashboard", "comptes", "stats", "eleves", "classes", "cycles",
                       "notes", "presences", "planning", "caisse", "tarifs",
                       "paiements", "personnel", "programmes", "parametres",
                       "bloc_notes", "calendrier", "documents", "reseau", "rapports"],
        # Le gestionnaire n'a PAS acces au personnel/RH, aux parametres
        # de l'etablissement ni a la gestion des comptes.
        "gestionnaire": ["dashboard", "stats", "eleves", "classes", "cycles", "notes",
                          "presences", "planning", "caisse", "tarifs", "paiements",
                          "programmes", "bloc_notes", "calendrier", "documents",
                          "reseau", "rapports"],
    }

    # Pages reservees au directeur, interdites d'edition pour les autres.
    DIRECTEUR_ONLY = ("comptes", "parametres", "personnel")

    def __init__(self, role):
        self.role = role if role in ROLES else "gestionnaire"

    def allowed(self, page):
        return page in self.NAV.get(self.role, [])

    def can_edit(self, page):
        if not self.allowed(page):
            return False
        if page in self.DIRECTEUR_ONLY:
            return self.role == "directeur"
        return True
