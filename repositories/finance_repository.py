import csv
import uuid
from urllib.parse import quote

from database import db
from repositories.base import RepositoryBase, _gen_reference


class FinanceRepository(RepositoryBase):

    def transactions(self, type_filtre=None, recherche="", date_start=None, date_end=None,
                     annee=None):

        sql = "SELECT * FROM transactions WHERE 1=1"
        params = []
        if type_filtre == "entree":
            sql += " AND type = 'entree'"
        elif type_filtre == "sortie":
            sql += " AND type = 'sortie'"
        if annee:
            sql += " AND (annee_scolaire = ? OR annee_scolaire IS NULL)"
            params.append(annee)
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
        active = db.query_one(
            "SELECT libelle FROM annees_scolaires WHERE est_active = 1")
        annee = active["libelle"] if active else None
        uuid_client = str(uuid.uuid4())
        payload = {"reference": reference, "beneficiaire": beneficiaire, "motif": motif,
                   "categorie": categorie, "montant": montant,
                   "type": type_trans, "mode_reglement": mode,
                   "annee_scolaire": annee, "uuid_client": uuid_client}
        self._route_write(
            "POST", "/paiement", payload,
            db.execute,
            """INSERT INTO transactions (reference, beneficiaire, motif, categorie, montant, type, mode_reglement, annee_scolaire, uuid_client)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (reference, beneficiaire, motif, categorie, montant, type_trans, mode, annee, uuid_client))
        return reference

    def delete_transaction(self, transaction_id):
        ligne = db.query_one("SELECT * FROM transactions WHERE id = ?",
                             (transaction_id,))
        if not ligne:
            return
        if ligne["paiement_id"] is not None:
            self._supprimer_paiement(ligne["paiement_id"])
            return
        reference = ligne["reference"]
        uuid_client = ligne.get("uuid_client")
        if reference and uuid_client:
            self._route_write("DELETE", f"/supprimerPaiement/{quote(reference)}",
                              {"uuid_client": uuid_client},
                              db.execute, "DELETE FROM transactions WHERE id = ?",
                              (transaction_id,))
        elif reference:
            self._route_write("DELETE", f"/supprimerPaiement/{quote(reference)}", {},
                              db.execute, "DELETE FROM transactions WHERE id = ?",
                              (transaction_id,))

    def caisse_totals(self):

        row = db.query_one(
            """SELECT COALESCE(SUM(CASE WHEN type = 'entree' THEN montant ELSE 0 END), 0) AS entree,
                      COALESCE(SUM(CASE WHEN type = 'sortie' THEN montant ELSE 0 END), 0) AS sortie
               FROM transactions""")
        entree = row["entree"] if row else 0
        sortie = row["sortie"] if row else 0
        return entree, sortie, entree - sortie

    def export_transactions_csv(self, path, type_filtre=None, recherche="",
                                date_start=None, date_end=None, annee=None):
        # Meme filtrage que la vue : l'export doit correspondre a l'affiche.
        rows = self.transactions(type_filtre=type_filtre, recherche=recherche,
                                 date_start=date_start, date_end=date_end,
                                 annee=annee)
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow(["Date", "Reference", "Beneficiaire", "Motif", "Categorie", "Type", "Montant", "Mode", "Annee"])
            for r in rows:
                writer.writerow([r["date"], r["reference"], r["beneficiaire"], r["motif"],
                                 r["categorie"], r["type"], r["montant"], r["mode_reglement"],
                                 r.get("annee_scolaire") or "-"])


    def tarifs(self, classe_id=None):
        sql = """SELECT t.*, c.nom AS classe_nom
                 FROM tarifs t LEFT JOIN classes c ON c.id = t.classe_id WHERE 1=1"""
        params = []
        if classe_id:
            sql += " AND t.classe_id = ?"
            params.append(classe_id)
        sql += " ORDER BY c.nom, t.type_frais"
        return db.query(sql, params)

    def _classe_nom(self, classe_id):
        if not classe_id:
            return None
        row = db.query_one("SELECT nom FROM classes WHERE id = ?", (classe_id,))
        return row["nom"] if row else None

    def add_tarif(self, classe_id, type_frais, montant, annee_scolaire=""):
        classe_nom = self._classe_nom(classe_id)
        payload = {"classe_id": classe_id, "type_frais": type_frais,
                   "montant": montant, "annee_scolaire": annee_scolaire,
                   "classe_nom": classe_nom}
        return self._route_write(
            "POST", "/tarifs-scolarite", payload,
            db.execute,
            "INSERT INTO tarifs (classe_id, type_frais, montant, annee_scolaire) VALUES (?, ?, ?, ?)",
            (classe_id, type_frais, montant, annee_scolaire))

    def update_tarif(self, tarif_id, classe_id, type_frais, montant, annee_scolaire=""):
        classe_nom = self._classe_nom(classe_id)
        payload = {"classe_id": classe_id, "type_frais": type_frais,
                   "montant": montant, "annee_scolaire": annee_scolaire,
                   "classe_nom": classe_nom}
        self._route_write(
            "PUT", f"/tarifs-scolarite/{tarif_id}", payload,
            db.execute,
            "UPDATE tarifs SET classe_id = ?, type_frais = ?, montant = ?, annee_scolaire = ? WHERE id = ?",
            (classe_id, type_frais, montant, annee_scolaire, tarif_id))

    def delete_tarif(self, tarif_id):
        row = db.query_one(
            """SELECT c.nom AS classe_nom, t.type_frais, t.annee_scolaire
               FROM tarifs t LEFT JOIN classes c ON c.id = t.classe_id
               WHERE t.id = ?""", (tarif_id,))
        payload = {"classe_nom": row["classe_nom"] if row else None,
                   "type_frais": row["type_frais"] if row else None,
                   "annee_scolaire": row["annee_scolaire"] if row else None}
        self._route_write("DELETE", f"/tarifs-scolarite/{tarif_id}", payload,
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

    def _ecriture_existe(self, paiement_id):
        row = db.query_one(
            "SELECT id FROM transactions WHERE paiement_id = ?",
            (paiement_id,))
        return row is not None

    def _creer_ecriture_caisse(self, paiement_id):
        """Ecriture de caisse (type 'entree') liee a un paiement d'eleve.

        C'est ce qui rend un encaissement visible dans la Caisse (qui ne
        lit que la table `transactions`) et dans tous les agregats qui en
        dependent : solde, export, encaissements du jour, tresorerie.

        Idempotente : si une ecriture existe deja pour ce paiement (que ce
        soit via l'insertion atomique de `add_paiement`, la reconciliation
        ou un pull precedent), elle est laissee intacte.
        """
        if self._ecriture_existe(paiement_id):
            return
        p = db.query_one(
            """SELECT p.*, e.prenom, e.nom
               FROM paiements p JOIN eleves e ON e.id = p.eleve_id
               WHERE p.id = ?""", (paiement_id,))
        if not p:
            return
        reference = _gen_reference("REC")
        beneficiaire = (
            f"{p['prenom'] or ''} {p['nom'] or ''}".strip() or "-")
        uuid_client = str(uuid.uuid4())
        db.execute(
            """INSERT INTO transactions
                   (date, reference, beneficiaire, motif, categorie, montant,
                    type, mode_reglement, annee_scolaire, paiement_id, uuid_client)
              VALUES (?, ?, ?, ?, ?, ?, 'entree', ?, ?, ?, ?)""",
            (p["date_paiement"], reference, beneficiaire,
             p["type_frais"] or "Paiement", p["type_frais"] or "Autres",
             p["montant"], p["mode_reglement"], p["annee_scolaire"], paiement_id, uuid_client))

    def reconcilier_caisse(self):
        """Cree les ecritures de caisse manquantes pour les paiements qui
        n'en ont pas encore (paiements anciens, paiements rapatries par la
        synchro, ou encaissements crees par un chemin sans ecriture).

        Rend la Caisse coherente avec la liste des Paiements : chaque
        paiement doit avoir exactement UNE ecriture 'entree' associee.
        Idempotente : reappeler ne cree rien. Retourne le nombre d'ecritures
        creees.
        """
        orphelins = db.query(
            """SELECT p.id FROM paiements p
               LEFT JOIN transactions t ON t.paiement_id = p.id
               WHERE t.id IS NULL""")
        for row in orphelins:
            self._creer_ecriture_caisse(row["id"])
        return len(orphelins)

    def _supprimer_paiement(self, paiement_id):
        row = db.query_one(
            """SELECT p.uuid_client, e.uuid_client AS eleve_uuid, p.montant, p.trimestre,
                      p.type_frais, p.annee_scolaire
               FROM paiements p JOIN eleves e ON e.id = p.eleve_id
               WHERE p.id = ?""", (paiement_id,))
        if row and row["uuid_client"]:
            ref = "|".join("" if row[k] is None else str(row[k])
                           for k in ("uuid_client", "montant", "trimestre",
                                     "type_frais", "annee_scolaire"))
            with db.transaction() as txn:
                txn.execute("DELETE FROM paiements WHERE id = ?", (paiement_id,))
                txn.execute("DELETE FROM transactions WHERE paiement_id = ?",
                            (paiement_id,))
            self._route_write("DELETE", f"/supprimerPaiement/{quote(ref)}",
                              {"uuid_client": row["uuid_client"]},
                              lambda *a, **kw: None)
        elif row:
            with db.transaction() as txn:
                txn.execute("DELETE FROM paiements WHERE id = ?", (paiement_id,))
                txn.execute("DELETE FROM transactions WHERE paiement_id = ?",
                            (paiement_id,))

    def add_paiement(self, eleve_id, montant, mode_reglement, type_frais,
                     annee_scolaire="", trimestre=""):
        eleve = db.query_one(
            """SELECT e.uuid_client, e.nom, e.prenom, c.nom AS classe_nom
               FROM eleves e LEFT JOIN classes c ON c.id = e.classe_id
               WHERE e.id = ?""",
            (eleve_id,))
        # Génère un uuid_client stable si absent
        uuid_client = eleve["uuid_client"] if eleve and eleve["uuid_client"] else str(uuid.uuid4())
        if eleve and not eleve["uuid_client"]:
            db.execute("UPDATE eleves SET uuid_client = ? WHERE id = ?", (uuid_client, eleve_id))
        payload = {"eleve_id": eleve_id, "montant": montant,
                   "mode_reglement": mode_reglement, "type_frais": type_frais,
                   "annee_scolaire": annee_scolaire, "trimestre": trimestre,
                   "eleve_uuid": uuid_client,
                   "classe_nom": eleve["classe_nom"] if eleve else None,
                   "uuid_client": uuid_client}

        def _inserer_paiement_et_caisse():
            """Insertion atomique : le paiement ET son ecriture de caisse
            ('entree' lise par la Caisse) sont creees dans la meme
            transaction, sinon un encaissement sans trace de caisse
            corromprait les soldes et la tresorerie."""
            beneficiaire = (
                f"{eleve['prenom'] or ''} {eleve['nom'] or ''}".strip()
                if eleve else "-")
            with db.transaction() as txn:
                cur = txn.execute(
                    """INSERT INTO paiements (eleve_id, montant, mode_reglement, type_frais,
                                              date_paiement, annee_scolaire, trimestre, uuid_client)
                           VALUES (?, ?, ?, ?, date('now', 'localtime'), ?, ?, ?)""",
                        (eleve_id, montant, mode_reglement, type_frais,
                         annee_scolaire, trimestre, uuid_client))
                paiement_id = cur.lastrowid
                txn.execute(
                    """INSERT INTO transactions
                           (date, reference, beneficiaire, motif, categorie, montant,
                            type, mode_reglement, annee_scolaire, paiement_id, uuid_client)
                      VALUES (date('now', 'localtime'), ?, ?, ?, ?, ?, 'entree', ?, ?, ?, ?)""",
                    (_gen_reference("REC"), beneficiaire,
                     type_frais or "Paiement", type_frais or "Autres",
                     montant, mode_reglement, annee_scolaire, paiement_id, str(uuid.uuid4())))
            return paiement_id

        return self._route_write("POST", "/paiement", payload,
                                 _inserer_paiement_et_caisse)

    def delete_paiement(self, paiement_id):
        self._supprimer_paiement(paiement_id)

    def solde_eleve(self, eleve_id, annee_scolaire=""):
        eleve = db.query_one("SELECT * FROM eleves WHERE id = ?", (eleve_id,))
        if not eleve:
            return {"attendu": 0.0, "paye": 0.0, "solde": 0.0}
        attendu_sql = "SELECT COALESCE(SUM(montant), 0) AS m FROM tarifs WHERE classe_id = ?"
        attendu_params = [eleve["classe_id"]]
        if annee_scolaire:
            attendu_sql += " AND annee_scolaire = ?"
            attendu_params.append(annee_scolaire)
        # classe_id NULL (donnee incomplete) -> attendu 0 : comportement
        # voulu, l'eleve sans classe n'est pas facturable tant qu'elle
        # n'est pas renseignee.
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