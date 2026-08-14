
from database import db
from repositories.base import RepositoryBase


class EleveRepository(RepositoryBase):

    def eleves(self, classe_id=None, statut=None, recherche=""):

        sql = """SELECT e.*, c.nom AS classe_nom
                 FROM eleves e LEFT JOIN classes c ON c.id = e.classe_id WHERE 1=1"""
        params = []
        if classe_id:
            sql += " AND e.classe_id = ?"
            params.append(classe_id)
        if statut and statut != "Tous les statuts":
            sql += " AND e.statut = ?"
            params.append(statut)
        if recherche:
            sql += " AND (e.nom LIKE ? OR e.prenom LIKE ? OR e.matricule LIKE ?)"
            like = f"%{recherche}%"
            params += [like, like, like]
        sql += " ORDER BY e.nom, e.prenom"
        return db.query(sql, params)

    def eleve_by_id(self, eleve_id):
        return db.query_one("SELECT * FROM eleves WHERE id = ?", (eleve_id,))

    def eleve_by_matricule(self, matricule):
        return db.query_one("SELECT * FROM eleves WHERE matricule = ?", (matricule,))

    def add_eleve(self, data):

        if not data.get("matricule"):
            data["matricule"] = self.next_matricule()
        data = dict(data)
        data.setdefault("check_acte", 0)
        data.setdefault("check_photos", 0)
        data.setdefault("check_bulletin", 0)
        data.setdefault("statut", "Inscrit")
        cols = [
            "matricule", "nom", "prenom", "sexe", "date_naissance", "lieu_naissance",
            "classe_id", "ecole_provenance", "pere_nom", "pere_tel", "mere_nom",
            "mere_tel", "tuteur_nom", "tuteur_tel", "adresse", "check_acte",
            "check_photos", "check_bulletin", "statut",
        ]
        sql = "INSERT INTO eleves (" + ", ".join(cols) + ") VALUES (" + ", ".join("?" for _ in cols) + ")"
        return self._route_write("POST", "/eleve", data,
                                 db.execute, sql, tuple(data.get(c) for c in cols))

    def update_eleve(self, eleve_id, data):
        cols = [
            "matricule", "nom", "prenom", "sexe", "date_naissance", "lieu_naissance",
            "classe_id", "ecole_provenance", "pere_nom", "pere_tel", "mere_nom",
            "mere_tel", "tuteur_nom", "tuteur_tel", "adresse", "check_acte",
            "check_photos", "check_bulletin", "statut",
        ]
        set_clause = ", ".join(f"{c} = ?" for c in cols)
        self._route_write("PUT", f"/modifierEleve/{eleve_id}", data,
                          db.execute,
                          f"UPDATE eleves SET {set_clause} WHERE id = ?",
                          tuple(data.get(c) for c in cols) + (eleve_id,))

    def delete_eleve(self, eleve_id):
        db.execute("DELETE FROM notes WHERE eleve_id = ?", (eleve_id,))
        self._route_write("DELETE", f"/eleve/{eleve_id}", {},
                          db.execute, "DELETE FROM eleves WHERE id = ?", (eleve_id,))

    def next_matricule(self):

        year = __import__("datetime").date.today().year
        prefix = f"ELEV{year}"
        row = db.query_one(
            "SELECT matricule FROM eleves WHERE matricule LIKE ? ORDER BY matricule DESC LIMIT 1",
            (f"{prefix}%",))
        if row:
            try:
                num = int(row["matricule"].replace(prefix, "")) + 1
            except ValueError:
                num = 1
        else:
            num = 1
        return f"{prefix}{num:04d}"
