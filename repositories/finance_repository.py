
import csv

from database import db
from repositories.base import RepositoryBase, _gen_reference


class FinanceRepository(RepositoryBase):

    def transactions(self, type_filtre=None, recherche="", date_start=None, date_end=None):

        sql = "SELECT * FROM transactions WHERE 1=1"
        params = []
        if type_filtre == "entree":
            sql += " AND type = 'entree'"
        elif type_filtre == "sortie":
            sql += " AND type = 'sortie'"
        if recherche:
            sql += " AND (beneficiaire LIKE ? OR motif LIKE ? OR reference LIKE ?)"
            like = f"%{recherche}%"
            params += [like, like, like]
        if date_start:
            sql += " AND date >= ?"
            params.append(date_start)
        if date_end:
            sql += " AND date <= ?"
            params.append(date_end)
        sql += " ORDER BY date DESC, id DESC"
        return db.query(sql, params)

    def add_transaction(self, type_trans, montant, motif, categorie, beneficiaire, mode=None):

        reference = _gen_reference("REC" if type_trans == "entree" else "DEP")
        payload = {"reference": reference, "beneficiaire": beneficiaire, "motif": motif,
                   "categorie": categorie, "montant": montant,
                   "type": type_trans, "mode_reglement": mode}
        self._route_write(
            "POST", "/paiement", payload,
            db.execute,
            """INSERT INTO transactions (reference, beneficiaire, motif, categorie, montant, type, mode_reglement)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (reference, beneficiaire, motif, categorie, montant, type_trans, mode))
        return reference

    def delete_transaction(self, transaction_id):
        self._route_write("DELETE", f"/supprimerPaiement/{transaction_id}", {},
                          db.execute, "DELETE FROM transactions WHERE id = ?", (transaction_id,))

    def caisse_totals(self):

        row = db.query_one(
            """SELECT COALESCE(SUM(CASE WHEN type = 'entree' THEN montant ELSE 0 END), 0) AS entree,
                      COALESCE(SUM(CASE WHEN type = 'sortie' THEN montant ELSE 0 END), 0) AS sortie
               FROM transactions""")
        entree = row["entree"] if row else 0
        sortie = row["sortie"] if row else 0
        return entree, sortie, entree - sortie

    def export_transactions_csv(self, path):
        rows = self.transactions()
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow(["Date", "Reference", "Beneficiaire", "Motif", "Categorie", "Type", "Montant", "Mode"])
            for r in rows:
                writer.writerow([r["date"], r["reference"], r["beneficiaire"], r["motif"],
                                 r["categorie"], r["type"], r["montant"], r["mode_reglement"]])


    def tarifs(self, classe_id=None):
        sql = """SELECT t.*, c.nom AS classe_nom
                 FROM tarifs t LEFT JOIN classes c ON c.id = t.classe_id WHERE 1=1"""
        params = []
        if classe_id:
            sql += " AND t.classe_id = ?"
            params.append(classe_id)
        sql += " ORDER BY c.nom, t.type_frais"
        return db.query(sql, params)

    def add_tarif(self, classe_id, type_frais, montant, annee_scolaire=""):
        payload = {"classe_id": classe_id, "type_frais": type_frais,
                   "montant": montant, "annee_scolaire": annee_scolaire}
        return self._route_write(
            "POST", "/tarifs-scolarite", payload,
            db.execute,
            "INSERT INTO tarifs (classe_id, type_frais, montant, annee_scolaire) VALUES (?, ?, ?, ?)",
            (classe_id, type_frais, montant, annee_scolaire))

    def update_tarif(self, tarif_id, classe_id, type_frais, montant, annee_scolaire=""):
        payload = {"classe_id": classe_id, "type_frais": type_frais,
                   "montant": montant, "annee_scolaire": annee_scolaire}
        self._route_write(
            "PUT", f"/tarifs-scolarite/{tarif_id}", payload,
            db.execute,
            "UPDATE tarifs SET classe_id = ?, type_frais = ?, montant = ?, annee_scolaire = ? WHERE id = ?",
            (classe_id, type_frais, montant, annee_scolaire, tarif_id))

    def delete_tarif(self, tarif_id):
        self._route_write("DELETE", f"/tarifs-scolarite/{tarif_id}", {},
                          db.execute, "DELETE FROM tarifs WHERE id = ?", (tarif_id,))


    def paiements(self, classe_id=None, type_frais=None, annee_scolaire=None,
                  mode=None, trimestre=None, nom=None, prenom=None):
        sql = """SELECT p.*, e.nom, e.prenom, e.matricule, c.nom AS classe_nom
                 FROM paiements p
                 JOIN eleves e ON e.id = p.eleve_id
                 LEFT JOIN classes c ON c.id = e.classe_id
                 WHERE 1=1"""
        params = []
        if classe_id:
            sql += " AND e.classe_id = ?"
            params.append(classe_id)
        if type_frais:
            sql += " AND p.type_frais = ?"
            params.append(type_frais)
        if annee_scolaire:
            sql += " AND p.annee_scolaire = ?"
            params.append(annee_scolaire)
        if mode:
            sql += " AND p.mode_reglement = ?"
            params.append(mode)
        if trimestre:
            sql += " AND p.trimestre = ?"
            params.append(trimestre)
        if nom:
            sql += " AND e.nom = ?"
            params.append(nom)
        if prenom:
            sql += " AND e.prenom = ?"
            params.append(prenom)
        sql += " ORDER BY p.date_paiement DESC, p.id DESC"
        return db.query(sql, params)

    def add_paiement(self, eleve_id, montant, mode_reglement, type_frais,
                     annee_scolaire="", trimestre=""):
        payload = {"eleve_id": eleve_id, "montant": montant,
                   "mode_reglement": mode_reglement, "type_frais": type_frais,
                   "annee_scolaire": annee_scolaire, "trimestre": trimestre}
        return self._route_write(
            "POST", "/paiement", payload,
            db.execute,
            """INSERT INTO paiements (eleve_id, montant, mode_reglement, type_frais,
                                      date_paiement, annee_scolaire, trimestre)
               VALUES (?, ?, ?, ?, date('now', 'localtime'), ?, ?)""",
            (eleve_id, montant, mode_reglement, type_frais, annee_scolaire, trimestre))

    def delete_paiement(self, paiement_id):
        self._route_write("DELETE", f"/supprimerPaiement/{paiement_id}", {},
                          db.execute, "DELETE FROM paiements WHERE id = ?", (paiement_id,))

    def solde_eleve(self, eleve_id, annee_scolaire=""):
        eleve = db.query_one("SELECT * FROM eleves WHERE id = ?", (eleve_id,))
        if not eleve:
            return {"attendu": 0.0, "paye": 0.0, "solde": 0.0}
        attendu_sql = "SELECT COALESCE(SUM(montant), 0) AS m FROM tarifs WHERE classe_id = ?"
        attendu_params = [eleve["classe_id"]]
        if annee_scolaire:
            attendu_sql += " AND annee_scolaire = ?"
            attendu_params.append(annee_scolaire)
        attendu = db.query_one(attendu_sql, attendu_params)["m"]
        paye_sql = "SELECT COALESCE(SUM(montant), 0) AS m FROM paiements WHERE eleve_id = ?"
        paye_params = [eleve_id]
        if annee_scolaire:
            paye_sql += " AND annee_scolaire = ?"
            paye_params.append(annee_scolaire)
        paye = db.query_one(paye_sql, paye_params)["m"]
        return {"attendu": attendu, "paye": paye, "solde": attendu - paye}

    def suivi_mensuel(self, eleve_id, annee_scolaire=""):
        if not annee_scolaire:
            annee = db.query_one("SELECT * FROM annees_scolaires WHERE est_active = 1")
            annee_scolaire = annee["libelle"] if annee else ""
        mois_noms = ["Septembre", "Octobre", "Novembre", "Decembre",
                     "Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin"]
        mois_nums = ["09", "10", "11", "12", "01", "02", "03", "04", "05", "06"]
        attendu_total = self.solde_eleve(eleve_id, annee_scolaire)["attendu"]
        mensuel = attendu_total / len(mois_nums) if attendu_total else 0.0
        rows = db.query(
            """SELECT strftime('%m', date_paiement) AS mois,
                      SUM(montant) AS total
               FROM paiements WHERE eleve_id = ? AND annee_scolaire = ?
               GROUP BY mois""", (eleve_id, annee_scolaire))
        par_mois = {r["mois"]: r["total"] for r in rows}
        suivi = []
        for nom, num in zip(mois_noms, mois_nums):
            suivi.append({"mois": nom, "attendu": round(mensuel, 2),
                          "paye": float(par_mois.get(num, 0) or 0)})
        return suivi

    def bilan_total(self, **filtres):
        rows = self.paiements(**filtres)
        return sum(float(r["montant"]) for r in rows)
