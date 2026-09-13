
from urllib.parse import quote

from database import db
from repositories.base import RepositoryBase


class ClasseRepository(RepositoryBase):

    def classes(self):
        return db.query(
            """SELECT c.*, cyc.nom AS cycle_nom,
                     (SELECT COUNT(*) FROM eleves e WHERE e.classe_id = c.id) AS effectif
               FROM classes c LEFT JOIN cycles cyc ON cyc.id = c.cycle_id
               ORDER BY c.nom""")

    def classe_by_id(self, classe_id):
        return db.query_one("SELECT * FROM classes WHERE id = ?", (classe_id,))

    def add_classe(self, nom, niveau, capacite, salle, titulaire, cycle_id=None):
        cycle_nom = self._cycle_nom(cycle_id)
        return self._route_write(
            "POST", "/classe",
            {"nom": nom, "niveau": niveau, "capacite": capacite,
             "salle": salle, "titulaire": titulaire, "cycle_id": cycle_id,
             "cycle_nom": cycle_nom},
            db.execute,
            "INSERT INTO classes (nom, niveau, capacite, salle, titulaire, cycle_id) VALUES (?, ?, ?, ?, ?, ?)",
            (nom, niveau, capacite, salle, titulaire, cycle_id))

    def update_classe(self, classe_id, nom, niveau, capacite, salle, titulaire, cycle_id=None):
        ancien = db.query_one(
            """SELECT c.nom AS nom, cyc.nom AS cycle_nom
               FROM classes c LEFT JOIN cycles cyc ON cyc.id = c.cycle_id
               WHERE c.id = ?""", (classe_id,))
        ancien_nom = ancien["nom"] if ancien else None
        self._route_write(
            "PUT", f"/modifierClasse/{classe_id}",
            {"nom": nom, "niveau": niveau, "capacite": capacite,
             "salle": salle, "titulaire": titulaire, "cycle_id": cycle_id,
             "cycle_nom": self._cycle_nom(cycle_id),
             "classe_ancien_nom": ancien_nom},
            db.execute,
            """UPDATE classes SET nom = ?, niveau = ?, capacite = ?, salle = ?, titulaire = ?,
               cycle_id = ? WHERE id = ?""",
            (nom, niveau, capacite, salle, titulaire, cycle_id, classe_id))

    def delete_classe(self, classe_id):
        eleves = db.query("SELECT id FROM eleves WHERE classe_id = ?", (classe_id,))
        eleve_ids = [e["id"] for e in eleves]
        for eid in eleve_ids:
            db.execute("DELETE FROM notes WHERE eleve_id = ?", (eid,))
            db.execute("DELETE FROM presences WHERE eleve_id = ?", (eid,))
            db.execute("DELETE FROM paiements WHERE eleve_id = ?", (eid,))
        db.execute("DELETE FROM eleves WHERE classe_id = ?", (classe_id,))
        db.execute("DELETE FROM planning WHERE classe_id = ?", (classe_id,))
        db.execute("DELETE FROM tarifs WHERE classe_id = ?", (classe_id,))
        db.execute("DELETE FROM programmes WHERE classe_id = ?", (classe_id,))
        ligne = db.query_one("SELECT nom FROM classes WHERE id = ?", (classe_id,))
        nom = ligne["nom"] if ligne else None
        # Le serveur accepte aussi un libelle (fallback par nom) :
        # pas d'id local pousse brut.
        endpoint = f"/supprimerClasse/{quote(str(nom))}" if nom else None
        if endpoint:
            self._route_write("DELETE", endpoint, {},
                              db.execute, "DELETE FROM classes WHERE id = ?", (classe_id,))


    def cycles(self):
        return db.query("SELECT * FROM cycles ORDER BY nom")

    def cycle_by_id(self, cycle_id):
        return db.query_one("SELECT * FROM cycles WHERE id = ?", (cycle_id,))

    def _cycle_nom(self, cycle_id):
        if not cycle_id:
            return None
        row = db.query_one("SELECT nom FROM cycles WHERE id = ?", (cycle_id,))
        return row["nom"] if row else None

    def add_cycle(self, nom, description=""):
        return self._route_write(
            "POST", "/cycle",
            {"nom": nom, "description": description},
            db.execute,
            "INSERT INTO cycles (nom, description) VALUES (?, ?)",
            (nom, description))

    def update_cycle(self, cycle_id, nom, description=""):
        ancien = self.cycle_by_id(cycle_id)
        self._route_write(
            "PUT", f"/modifierCycle/{cycle_id}",
            {"nom": nom, "description": description,
             "cycle_ancien_nom": ancien["nom"] if ancien else None},
            db.execute,
            "UPDATE cycles SET nom = ?, description = ? WHERE id = ?",
            (nom, description, cycle_id))

    def delete_cycle(self, cycle_id):
        db.execute("UPDATE classes SET cycle_id = NULL WHERE cycle_id = ?", (cycle_id,))
        ancien = self.cycle_by_id(cycle_id)
        self._route_write("DELETE", f"/supprimerCycle/{cycle_id}",
                          {"cycle_nom": ancien["nom"] if ancien else None},
                          db.execute, "DELETE FROM cycles WHERE id = ?", (cycle_id,))

    def annees_scolaires(self):
        return db.query(
            "SELECT * FROM annees_scolaires ORDER BY est_active DESC, date_debut DESC")

    def annee_scolaire_active(self):
        return db.query_one("SELECT * FROM annees_scolaires WHERE est_active = 1")

    def add_annee_scolaire(self, libelle, date_debut, date_fin, est_active=False):
        return self._route_write(
            "POST", "/ajouter_annee_scolaire",
            {"libelle": libelle, "date_debut": date_debut,
             "date_fin": date_fin, "est_active": est_active},
            db.execute,
            """INSERT INTO annees_scolaires (libelle, date_debut, date_fin, est_active)
               VALUES (?, ?, ?, ?)""",
            (libelle, date_debut, date_fin, 1 if est_active else 0))

    def update_annee_scolaire(self, annee_id, libelle, date_debut, date_fin, est_active=False):
        ancien = db.query_one("SELECT libelle FROM annees_scolaires WHERE id = ?", (annee_id,))
        self._route_write(
            "PUT", f"/annee_scolaire/{annee_id}",
            {"libelle": libelle, "date_debut": date_debut,
             "date_fin": date_fin, "est_active": est_active,
             "annee_ancien_libelle": ancien["libelle"] if ancien else None},
            db.execute,
            """UPDATE annees_scolaires SET libelle = ?, date_debut = ?, date_fin = ?, est_active = ?
               WHERE id = ?""",
            (libelle, date_debut, date_fin, 1 if est_active else 0, annee_id))

    def set_annee_active(self, annee_id):
        def _update():
            conn = db.connect()
            try:
                conn.execute("UPDATE annees_scolaires SET est_active = 0")
                conn.execute("UPDATE annees_scolaires SET est_active = 1 WHERE id = ?", (annee_id,))
                conn.commit()
            finally:
                conn.close()
        libelle = db.query_one("SELECT libelle FROM annees_scolaires WHERE id = ?", (annee_id,))
        self._route_write("PUT", f"/annee_scolaire/{annee_id}/actif",
                          {"est_active": True,
                           "annee_libelle": libelle["libelle"] if libelle else None},
                          _update)

    def delete_annee_scolaire(self, annee_id):
        libelle = db.query_one("SELECT libelle FROM annees_scolaires WHERE id = ?", (annee_id,))
        self._route_write("DELETE", f"/annee_scolaire/{annee_id}",
                          {"annee_libelle": libelle["libelle"] if libelle else None},
                          db.execute, "DELETE FROM annees_scolaires WHERE id = ?", (annee_id,))
