
from database import db
from repositories.base import RepositoryBase


class CompteRepository(RepositoryBase):

    def utilisateurs(self, role=None, recherche=""):

        sql = "SELECT id, nom_complet, username, email, telephone, role, actif, created_at, last_login FROM utilisateurs WHERE 1=1"
        params = []
        if role and role != "Tous les roles":
            sql += " AND role = ?"
            params.append(role.lower())
        if recherche:
            sql += " AND (nom_complet LIKE ? OR email LIKE ?)"
            like = f"%{recherche}%"
            params += [like, like]
        sql += " ORDER BY nom_complet"
        return db.query(sql, params)

    def add_compte(self, nom, role, password_hash, actif, email="", telephone=""):
        username = (email.split("@")[0] if email
                    else nom.lower().replace(" ", "."))
        base = username
        counter = 1
        while db.query_one("SELECT 1 FROM utilisateurs WHERE username = ?", (username,)):
            username = f"{base}{counter}"
            counter += 1
        self._route_write(
            "POST", "/comptes", {"nom": nom, "email": email, "telephone": telephone,
                                  "role": role, "actif": 1 if actif else 0,
                                  # Hash PBKDF2 transmis tel quel : le serveur
                                  # sait aussi le verifier (format salt:hash).
                                  "password": password_hash},
            db.execute,
            """INSERT INTO utilisateurs (nom_complet, username, email, telephone, password, role, actif)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (nom, username, email, telephone, password_hash, role, 1 if actif else 0))
        return username

    def update_compte(self, user_id, nom, role, actif):
        db.execute(
            """UPDATE utilisateurs SET nom_complet = ?, role = ?, actif = ?
               WHERE id = ?""",
            (nom, role, 1 if actif else 0, user_id))

    def toggle_compte(self, user_id, actif):
        db.execute("UPDATE utilisateurs SET actif = ? WHERE id = ?", (1 if actif else 0, user_id))

    def reset_password(self, user_id, password_hash):
        db.execute("UPDATE utilisateurs SET password = ? WHERE id = ?", (password_hash, user_id))

    def delete_compte(self, user_id):
        db.execute("DELETE FROM connexions WHERE utilisateur_id = ?", (user_id,))
        db.execute("DELETE FROM utilisateurs WHERE id = ?", (user_id,))
