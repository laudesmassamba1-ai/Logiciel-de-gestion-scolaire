# operations sur les classes, avec aiguillage vers le serveur si en ligne
from database import db
from repositories.base import RepositoryBase


class ClasseRepository(RepositoryBase):

    def classes(self):
        return db.query(
            """SELECT c.*, (SELECT COUNT(*) FROM eleves e WHERE e.classe_id = c.id) AS effectif
               FROM classes c ORDER BY c.nom""")

    def classe_by_id(self, classe_id):
        return db.query_one("SELECT * FROM classes WHERE id = ?", (classe_id,))

    def add_classe(self, nom, niveau, capacite, salle, titulaire):
        return self._route_write(
            "POST", "/classe",
            {"nom": nom, "niveau": niveau, "capacite": capacite,
             "salle": salle, "titulaire": titulaire},
            db.execute,
            "INSERT INTO classes (nom, niveau, capacite, salle, titulaire) VALUES (?, ?, ?, ?, ?)",
            (nom, niveau, capacite, salle, titulaire))

    def update_classe(self, classe_id, nom, niveau, capacite, salle, titulaire):
        self._route_write(
            "PUT", f"/modifierClasse/{classe_id}",
            {"nom": nom, "niveau": niveau, "capacite": capacite,
             "salle": salle, "titulaire": titulaire},
            db.execute,
            "UPDATE classes SET nom = ?, niveau = ?, capacite = ?, salle = ?, titulaire = ? WHERE id = ?",
            (nom, niveau, capacite, salle, titulaire, classe_id))

    def delete_classe(self, classe_id):
        # on efface d'abord ce qui depend de la classe (eleves, planning)
        db.execute("DELETE FROM eleves WHERE classe_id = ?", (classe_id,))
        db.execute("DELETE FROM planning WHERE classe_id = ?", (classe_id,))
        self._route_write("DELETE", f"/supprimerClasse/{classe_id}", {},
                          db.execute, "DELETE FROM classes WHERE id = ?", (classe_id,))
