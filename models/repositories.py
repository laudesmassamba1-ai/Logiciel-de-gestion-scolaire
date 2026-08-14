import csv
import uuid
from pathlib import Path

from database import db
from config import DOCS_DIR, JOURS, CRENEAUX

# cree une reference unique (par exemple REC-XXXX ou DEP-XXXX)
def _gen_reference(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

class Repositories:
    # toutes les operations sur la base de donnees passent par ici

    def classes(self):
        return db.query(
            """SELECT c.*, (SELECT COUNT(*) FROM eleves e WHERE e.classe_id = c.id) AS effectif
               FROM classes c ORDER BY c.nom""")

    def classe_by_id(self, classe_id):
        return db.query_one("SELECT * FROM classes WHERE id = ?", (classe_id,))

    def add_classe(self, nom, niveau, capacite, salle, titulaire):
        return db.execute(
            "INSERT INTO classes (nom, niveau, capacite, salle, titulaire) VALUES (?, ?, ?, ?, ?)",
            (nom, niveau, capacite, salle, titulaire))

    def update_classe(self, classe_id, nom, niveau, capacite, salle, titulaire):
        db.execute(
            "UPDATE classes SET nom = ?, niveau = ?, capacite = ?, salle = ?, titulaire = ? WHERE id = ?",
            (nom, niveau, capacite, salle, titulaire, classe_id))

    def delete_classe(self, classe_id):
        # on efface d'abord ce qui depend de la classe (eleves, planning)
        db.execute("DELETE FROM eleves WHERE classe_id = ?", (classe_id,))
        db.execute("DELETE FROM planning WHERE classe_id = ?", (classe_id,))
        db.execute("DELETE FROM classes WHERE id = ?", (classe_id,))

    def matieres(self):
        return db.query("SELECT * FROM matieres ORDER BY nom")

    def add_matiere(self, nom):
        return db.execute("INSERT OR IGNORE INTO matieres (nom) VALUES (?)", (nom,))

    def eleves(self, classe_id=None, statut=None, recherche=""):
        # liste les eleves, avec filtres optionnels (classe, statut, nom...)
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
        # cree un nouvel eleve ; si pas de matricule, on en genere un
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
        return db.execute(sql, tuple(data.get(c) for c in cols))

    def update_eleve(self, eleve_id, data):
        cols = [
            "matricule", "nom", "prenom", "sexe", "date_naissance", "lieu_naissance",
            "classe_id", "ecole_provenance", "pere_nom", "pere_tel", "mere_nom",
            "mere_tel", "tuteur_nom", "tuteur_tel", "adresse", "check_acte",
            "check_photos", "check_bulletin", "statut",
        ]
        set_clause = ", ".join(f"{c} = ?" for c in cols)
        db.execute(f"UPDATE eleves SET {set_clause} WHERE id = ?",
                   tuple(data.get(c) for c in cols) + (eleve_id,))

    def delete_eleve(self, eleve_id):
        db.execute("DELETE FROM notes WHERE eleve_id = ?", (eleve_id,))
        db.execute("DELETE FROM eleves WHERE id = ?", (eleve_id,))

    def next_matricule(self):
        # genere le prochain matricule de l'annee en cours (ex: ELEV2026-001)
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

    def notes_for(self, classe_id, matiere_id, periode):
        # recupere les notes d'une classe, d'une matiere et d'une periode donnee
        return db.query(
            """SELECT n.*, e.matricule, e.nom, e.prenom
               FROM notes n JOIN eleves e ON e.id = n.eleve_id
               WHERE e.classe_id = ? AND n.matiere_id = ? AND n.periode = ?
               ORDER BY e.nom, e.prenom""",
            (classe_id, matiere_id, periode))

    def save_note(self, eleve_id, matiere_id, periode, devoir1, devoir2, composition):
        # enregistre la note ; si elle existe deja, on la met a jour
        db.execute(
            """INSERT INTO notes (eleve_id, matiere_id, periode, devoir1, devoir2, composition)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (eleve_id, matiere_id, periode)
               DO UPDATE SET devoir1 = excluded.devoir1, devoir2 = excluded.devoir2,
                             composition = excluded.composition""",
            (eleve_id, matiere_id, periode, devoir1, devoir2, composition))

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
        db.execute(
            """INSERT INTO transactions (reference, beneficiaire, motif, categorie, montant, type, mode_reglement)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (reference, beneficiaire, motif, categorie, montant, type_trans, mode))
        return reference

    def delete_transaction(self, transaction_id):
        db.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))

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

    def utilisateurs(self, role=None, recherche=""):
        # liste les comptes utilisateurs, avec filtre par role ou nom
        sql = "SELECT id, nom_complet, username, email, telephone, role, actif, created_at, last_login FROM utilisateurs WHERE 1=1"
        params = []
        if role and role != "Tous les roles":
            sql += " AND role = ?"
            params.append(role.lower())
        if recherche:
            sql += " AND (nom_complet LIKE ? OR email LIKE ?)"
            like = f"%{recherche}%"
            params += [like, like]
        sql += " ORDER BY nom_complet"
        return db.query(sql, params)

    def add_compte(self, nom, email, telephone, role, password_hash, actif):
        username = email.split("@")[0] if email else nom.lower().replace(" ", ".")
        return db.execute(
            """INSERT INTO utilisateurs (nom_complet, username, email, telephone, password, role, actif)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (nom, username, email, telephone, password_hash, role, 1 if actif else 0))

    def update_compte(self, user_id, nom, email, telephone, role, actif):
        db.execute(
            """UPDATE utilisateurs SET nom_complet = ?, email = ?, telephone = ?, role = ?, actif = ?
               WHERE id = ?""",
            (nom, email, telephone, role, 1 if actif else 0, user_id))

    def toggle_compte(self, user_id, actif):
        db.execute("UPDATE utilisateurs SET actif = ? WHERE id = ?", (1 if actif else 0, user_id))

    def reset_password(self, user_id, password_hash):
        db.execute("UPDATE utilisateurs SET password = ? WHERE id = ?", (password_hash, user_id))

    def delete_compte(self, user_id):
        db.execute("DELETE FROM connexions WHERE utilisateur_id = ?", (user_id,))
        db.execute("DELETE FROM utilisateurs WHERE id = ?", (user_id,))

    def planning_for(self, classe_id):
        # recupere l'emploi du temps d'une classe
        rows = db.query(
            "SELECT * FROM planning WHERE classe_id = ?", (classe_id,))
        return {(r["jour"], r["creneau"]): r for r in rows}

    def save_planning(self, classe_id, entries):
        db.execute("DELETE FROM planning WHERE classe_id = ?", (classe_id,))
        db.executemany(
            "INSERT INTO planning (classe_id, jour, creneau, matiere, salle) VALUES (?, ?, ?, ?, ?)",
            [(classe_id, jour, creneau, matiere, salle) for (jour, creneau, matiere, salle) in entries])

    def personnel(self, recherche=""):
        sql = "SELECT * FROM personnel WHERE 1=1"
        params = []
        if recherche:
            sql += " AND nom_complet LIKE ?"
            params.append(f"%{recherche}%")
        sql += " ORDER BY nom_complet"
        return db.query(sql, params)

    def add_personnel(self, nom, fonction, telephone, email, salaire, statut):
        return db.execute(
            """INSERT INTO personnel (nom_complet, fonction, telephone, email, salaire, statut)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nom, fonction, telephone, email, salaire, statut))

    def update_personnel(self, pid, nom, fonction, telephone, email, salaire, statut):
        db.execute(
            """UPDATE personnel SET nom_complet = ?, fonction = ?, telephone = ?, email = ?,
               salaire = ?, statut = ? WHERE id = ?""",
            (nom, fonction, telephone, email, salaire, statut, pid))

    def delete_personnel(self, pid):
        db.execute("DELETE FROM personnel WHERE id = ?", (pid,))

    def masse_salariale(self):
        row = db.query_one("SELECT COALESCE(SUM(salaire), 0) AS s FROM personnel")
        return row["s"] if row else 0

    def enseignants(self):
        return db.query("SELECT * FROM personnel WHERE fonction LIKE '%Enseignant%'")

    def parametres(self):
        # renvoie les parametres (nom de l'ecole, ville, signataire...) sous forme de dictionnaire
        rows = db.query("SELECT cle, valeur FROM parametres")
        return {r["cle"]: r["valeur"] for r in rows}

    def set_parametre(self, cle, valeur):
        db.execute(
            "INSERT INTO parametres (cle, valeur) VALUES (?, ?) ON CONFLICT (cle) DO UPDATE SET valeur = excluded.valeur",
            (cle, valeur))

    def delete_parametres(self):
        for cle in ("signataire_nom", "signataire_titre", "ville"):
            db.execute("DELETE FROM parametres WHERE cle = ?", (cle,))
            db.execute("INSERT INTO parametres (cle, valeur) VALUES (?, '')", (cle,))

    def stats_dashboard(self):
        # les chiffres affiches sur le tableau de bord (effectifs, encaissements...)
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
