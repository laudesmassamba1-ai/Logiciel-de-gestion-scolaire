
from database import db
from repositories.base import RepositoryBase


class PedagogieRepository(RepositoryBase):

    def matieres(self):
        return db.query("SELECT * FROM matieres ORDER BY nom")

    def add_matiere(self, nom):
        return self._route_write("POST", "/matiere", {"nom": nom},
                                 db.execute,
                                 "INSERT OR IGNORE INTO matieres (nom) VALUES (?)", (nom,))

    def enseignants(self):
        return db.query("SELECT * FROM personnel WHERE fonction LIKE '%Enseignant%'")
