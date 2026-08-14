# operations sur la caisse, avec aiguillage vers le serveur si en ligne
import csv

from database import db
from repositories.base import RepositoryBase, _gen_reference


class FinanceRepository(RepositoryBase):

    def transactions(self, type_filtre=None, recherche="", date_start=None, date_end=None):
        # liste les mouvements de caisse (entrees / sorties) avec filtres
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
        # ajoute une entree ou une sortie dans la caisse
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
        # total des entrees, des sorties et solde de la caisse
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
