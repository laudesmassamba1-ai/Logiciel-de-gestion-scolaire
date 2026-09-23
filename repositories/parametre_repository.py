
from database import db
from repositories.base import RepositoryBase


class ParametreRepository(RepositoryBase):

    def parametres(self):

        rows = db.query("SELECT cle, valeur FROM parametres")
        return {r["cle"]: r["valeur"] for r in rows}

    def set_parametre(self, cle, valeur):
        self._route_write(
            "POST", "/parametre",
            {"cle": cle, "valeur": valeur},
            db.execute,
            "INSERT INTO parametres (cle, valeur) VALUES (?, ?) ON CONFLICT (cle) DO UPDATE SET valeur = excluded.valeur",
            (cle, valeur))

    def delete_parametres(self):
        for cle in ("nom_ecole", "signataire_nom", "signataire_titre", "ville", "pays"):
            self._route_write(
                "DELETE", f"/parametre/{cle}",
                {"cle": cle},
                db.execute,
                "DELETE FROM parametres WHERE cle = ?", (cle,))
            db.execute("INSERT INTO parametres (cle, valeur) VALUES (?, '')", (cle,))

    def stats_dashboard(self):

        total_eleves = db.query_one("SELECT COUNT(*) AS c FROM eleves")["c"]
        inscrits_jour = db.query_one(
            "SELECT COUNT(*) AS c FROM eleves WHERE date_inscription = date('now', 'localtime')")["c"]
        encaissements = db.query_one(
            """SELECT COALESCE(SUM(montant), 0) AS m FROM transactions
               WHERE type = 'entree' AND date = date('now', 'localtime')""")["m"]
        dossiers_incomplets = db.query_one(
            """SELECT COUNT(*) AS c FROM eleves
               WHERE check_acte = 0 OR check_photos = 0 OR check_bulletin = 0""")["c"]
        return {
            "total_eleves": total_eleves,
            "inscriptions_jour": inscrits_jour,
            "encaissements_jour": encaissements,
            "dossiers_incomplets": dossiers_incomplets,
        }
