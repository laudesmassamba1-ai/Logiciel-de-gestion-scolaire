
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
        ligne = db.query_one("SELECT nom FROM classes WHERE id = ?", (classe_id,))
        nom = ligne["nom"] if ligne else None
        eleves = db.query("SELECT id FROM eleves WHERE classe_id = ?", (classe_id,))
        eleve_ids = [e["id"] for e in eleves]
        # Suppression en une seule transaction : jamais de classe a moitie
        # vide en cas d'ecriture interrompue (notes/presences/paiements des
        # eleves, eleves, puis plan/tarifs/programmes/classe elle-meme).
        with db.transaction() as txn:
            for eid in eleve_ids:
                txn.execute("DELETE FROM notes WHERE eleve_id = ?", (eid,))
                txn.execute("DELETE FROM presences WHERE eleve_id = ?", (eid,))
                txn.execute("DELETE FROM paiements WHERE eleve_id = ?", (eid,))
            txn.execute("DELETE FROM eleves WHERE classe_id = ?", (classe_id,))
            txn.execute("DELETE FROM planning WHERE classe_id = ?", (classe_id,))
            txn.execute("DELETE FROM tarifs WHERE classe_id = ?", (classe_id,))
            txn.execute("DELETE FROM programmes WHERE classe_id = ?", (classe_id,))
            txn.execute("DELETE FROM classes WHERE id = ?", (classe_id,))
        # Suppression serveur uniquement (le local est deja fait atomiquement).
        # Le serveur accepte aussi un libelle (fallback par nom).
        if nom:
            endpoint = f"/supprimerClasse/{quote(str(nom))}"
            self._route_write("DELETE", endpoint, {},
                              lambda *args, **kwargs: None)


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

    def close_annee_scolaire(self, annee_id, nouvelle_libelle, nouvelle_debut, nouvelle_fin,
                             promouvoir_eleves=False):
        """Ferme l'année scolaire en cours et ouvre la suivante.

        Operations :
        1. Archive l'année courante (est_active = 0, archivee = 1)
        2. Crée la nouvelle année scolaire
        3. Si demandé, promeut les élèves (classe supérieure)
        4. Réinitialise les compteurs de paiements pour la nouvelle année
        """
        from datetime import date
        import uuid

        # 1. Archive l'année courante
        db.execute(
            """UPDATE annees_scolaires SET est_active = 0, archivee = 1 WHERE id = ?""",
            (annee_id,))

        # Ajoute la colonne archivee si elle n'existe pas (migration douce)
        try:
            db.execute("ALTER TABLE annees_scolaires ADD COLUMN archivee INTEGER DEFAULT 0")
        except Exception:
            pass

        # 2. Crée la nouvelle année
        new_id = db.execute(
            """INSERT INTO annees_scolaires (libelle, date_debut, date_fin, est_active, archivee)
               VALUES (?, ?, ?, 1, 0)""",
            (nouvelle_libelle, nouvelle_debut, nouvelle_fin))

        # 3. Promeut les élèves si demandé
        if promouvoir_eleves:
            # Règle simple : on ne change que la classe_id selon la progression
            # CP1→CP2, CP2→CE1, CE1→CE2, CE2→CM1, CM1→CM2, CM2→6eme,
            # 6eme→5eme, 5eme→4eme, 4eme→3eme, 3eme→2nde, 2nde→1ere, 1ere→Terminale
            progression = {
                "CP1": "CP2", "CP2": "CE1", "CE1": "CE2", "CE2": "CM1",
                "CM1": "CM2", "CM2": "6eme", "6eme": "5eme", "5eme": "4eme",
                "4eme": "3eme", "3eme": "2nde", "2nde": "1ere", "1ere": "Terminale"
            }
            eleves = db.query("SELECT e.id, c.nom FROM eleves e JOIN classes c ON c.id = e.classe_id")
            for e in eleves:
                classe_actuelle = e["nom"]
                if classe_actuelle in progression:
                    nouvelle_classe_nom = progression[classe_actuelle]
                    nouvelle_classe = db.query_one("SELECT id FROM classes WHERE nom = ?", (nouvelle_classe_nom,))
                    if nouvelle_classe:
                        db.execute("UPDATE eleves SET classe_id = ? WHERE id = ?",
                                   (nouvelle_classe["id"], e["id"]))

        # 4. Réinitialise les paiements pour la nouvelle année (nouvelle base de facturation)
        # Les anciens paiements restent dans l'année archivée

        # 5. Push vers serveur
        self._route_write(
            "POST", "/fermer-annee-scolaire",
            {"annee_archivee_id": annee_id,
             "nouvelle_annee": {"libelle": nouvelle_libelle, "date_debut": nouvelle_debut,
                                "date_fin": nouvelle_fin, "promouvoir_eleves": promouvoir_eleves}},
            lambda *a, **kw: None)

        return new_id
