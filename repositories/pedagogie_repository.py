from database import db
from repositories.base import RepositoryBase


class PedagogieRepository(RepositoryBase):

    def matieres(self):
        return db.query("SELECT * FROM matieres ORDER BY nom")

    def matiere_by_id(self, matiere_id):
        return db.query_one("SELECT * FROM matieres WHERE id = ?", (matiere_id,))

    def add_matiere(self, nom, coefficient=1):
        return self._route_write("POST", "/matiere", {"nom": nom, "coefficient": coefficient},
                                 db.execute,
                                 "INSERT OR IGNORE INTO matieres (nom, coefficient) VALUES (?, ?)",
                                 (nom, coefficient))

    def update_matiere(self, matiere_id, nom, coefficient):
        self._route_write("PUT", f"/modifierMatiere/{matiere_id}",
                          {"nom": nom, "coefficient": coefficient},
                          db.execute,
                          "UPDATE matieres SET nom = ?, coefficient = ? WHERE id = ?",
                          (nom, coefficient, matiere_id))

    def delete_matiere(self, matiere_id):
        db.execute("DELETE FROM programmes WHERE matiere_id = ?", (matiere_id,))
        db.execute("DELETE FROM notes WHERE matiere_id = ?", (matiere_id,))
        self._route_write("DELETE", f"/supprimerMatiere/{matiere_id}", {},
                          db.execute, "DELETE FROM matieres WHERE id = ?", (matiere_id,))

    def enseignants(self):
        return db.query(
            "SELECT * FROM personnel WHERE fonction LIKE '%Enseignant%' OR fonction LIKE '%Professeur%' OR fonction LIKE '%Instituteur%' ORDER BY nom_complet")

    def programmes(self, classe_id=None):
        sql = """SELECT p.*, m.nom AS matiere_nom, m.coefficient AS matiere_coeff,
                        c.nom AS classe_nom, pe.nom_complet AS enseignant_nom
                 FROM programmes p
                 JOIN matieres m ON m.id = p.matiere_id
                 JOIN classes c ON c.id = p.classe_id
                 LEFT JOIN personnel pe ON pe.id = p.enseignant_id
                 WHERE 1=1"""
        params = []
        if classe_id:
            sql += " AND p.classe_id = ?"
            params.append(classe_id)
        sql += " ORDER BY c.nom, m.nom"
        return db.query(sql, params)

    def save_programme(self, classe_id, matiere_id, enseignant_id, coefficient):
        payload = {"classe_id": classe_id, "matiere_id": matiere_id,
                   "enseignant_id": enseignant_id, "coefficient": coefficient}
        return self._route_write(
            "POST", "/associerMatiereClasseEnseignant", payload,
            db.execute,
            """INSERT INTO programmes (classe_id, matiere_id, enseignant_id, coefficient)
               VALUES (?, ?, ?, ?)
               ON CONFLICT (classe_id, matiere_id)
               DO UPDATE SET enseignant_id = excluded.enseignant_id,
                             coefficient = excluded.coefficient""",
            (classe_id, matiere_id, enseignant_id, coefficient))

    def delete_programme(self, prog_id):
        self._route_write("DELETE", f"/supprimerProgramme/{prog_id}", {},
                          db.execute, "DELETE FROM programmes WHERE id = ?", (prog_id,))
