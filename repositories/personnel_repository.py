
from database import db
from repositories.base import RepositoryBase


class PersonnelRepository(RepositoryBase):

    def personnel(self, recherche=""):
        sql = "SELECT * FROM personnel WHERE 1=1"
        params = []
        if recherche:
            sql += " AND nom_complet LIKE ?"
            params.append(f"%{recherche}%")
        sql += " ORDER BY nom_complet"
        return db.query(sql, params)

    def add_personnel(self, nom, fonction, telephone, email, salaire, statut):
        payload = {"nom_complet": nom, "fonction": fonction, "telephone": telephone,
                   "email": email, "salaire": salaire, "statut": statut}
        return self._route_write(
            "POST", "/enseignant", payload,
            db.execute,
            """INSERT INTO personnel (nom_complet, fonction, telephone, email, salaire, statut)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nom, fonction, telephone, email, salaire, statut))

    def update_personnel(self, pid, nom, fonction, telephone, email, salaire, statut):
        payload = {"nom_complet": nom, "fonction": fonction, "telephone": telephone,
                   "email": email, "salaire": salaire, "statut": statut}
        self._route_write(
            "PUT", f"/modifierEnseignant/{pid}", payload,
            db.execute,
            """UPDATE personnel SET nom_complet = ?, fonction = ?, telephone = ?, email = ?,
               salaire = ?, statut = ? WHERE id = ?""",
            (nom, fonction, telephone, email, salaire, statut, pid))

    def delete_personnel(self, pid):
        self._route_write("DELETE", f"/supprimerEnseignant/{pid}", {},
                          db.execute, "DELETE FROM personnel WHERE id = ?", (pid,))

    def masse_salariale(self):
        row = db.query_one("SELECT COALESCE(SUM(salaire), 0) AS s FROM personnel")
        return row["s"] if row else 0
