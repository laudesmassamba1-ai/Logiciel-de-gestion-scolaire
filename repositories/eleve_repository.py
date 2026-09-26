
import sqlite3
import uuid as _uuid
from database import db
from repositories.base import RepositoryBase


class EleveRepository(RepositoryBase):

    def eleves(self, classe_id=None, statut=None, recherche=""):

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
        data = dict(data)
        data.setdefault("check_acte", 0)
        data.setdefault("check_photos", 0)
        data.setdefault("check_bulletin", 0)
        data.setdefault("statut", "Inscrit")
        data.setdefault("redoublant", 0)
        if not data.get("uuid_client"):
            data["uuid_client"] = str(_uuid.uuid4())
        cols = [
            "matricule", "nom", "prenom", "sexe", "date_naissance", "lieu_naissance",
            "classe_id", "ecole_provenance", "pere_nom", "pere_tel", "mere_nom",
            "mere_tel", "tuteur_nom", "tuteur_tel", "adresse", "redoublant",
            "check_acte", "check_photos", "check_bulletin", "statut", "uuid_client",
            "photo",
        ]
        sql = "INSERT INTO eleves (" + ", ".join(cols) + ") VALUES (" + ", ".join("?" for _ in cols) + ")"
        classe_nom = self._classe_nom(data.get("classe_id"))
        # Le matricule est genere par MAX+1 sur la base LOCALE : deux postes
        # peuvent produire le meme numero (la sync deduplique par uuid_client,
        # pas par matricule). Si INSERT heurte la contrainte UNIQUE localement,
        # on regenere un numero et on retente (avant tout envoi serveur :
        # _route_write ecrit d'abord, donc un echec remonte sans envoi).
        for _ in range(5):
            if not data.get("matricule"):
                data["matricule"] = self.next_matricule()
            payload = dict(data)
            payload.pop("photo", None)
            if classe_nom:
                payload["classe_nom"] = classe_nom
            try:
                return self._route_write("POST", "/eleve", payload,
                                         db.execute, sql,
                                         tuple(data.get(c) for c in cols))
            except sqlite3.IntegrityError as exc:
                if "matricule" not in str(exc):
                    raise
                data["matricule"] = None
        raise sqlite3.IntegrityError(
            "impossible de generer un matricule unique (5 essais)")

    def update_eleve(self, eleve_id, data):
        data = dict(data)
        # La photo (locale) n'est modifiee que si la fiche l'a explicitement
        # changee (cle presente, vide = retiree) : un appelant partiel ne
        # doit jamais l'effacer par accident.
        if "photo" not in data:
            row = db.query_one("SELECT photo FROM eleves WHERE id = ?",
                               (eleve_id,))
            if row is not None:
                data["photo"] = row["photo"]
        data.setdefault("check_acte", 0)
        data.setdefault("check_photos", 0)
        data.setdefault("check_bulletin", 0)
        data.setdefault("statut", "Inscrit")
        data.setdefault("redoublant", 0)
        cols = [
            "matricule", "nom", "prenom", "sexe", "date_naissance", "lieu_naissance",
            "classe_id", "ecole_provenance", "pere_nom", "pere_tel", "mere_nom",
            "mere_tel", "tuteur_nom", "tuteur_tel", "adresse", "redoublant",
            "check_acte", "check_photos", "check_bulletin", "statut",
            "photo",
        ]
        tuple_vals = tuple(data.get(c) for c in cols) + (eleve_id,)
        uuid_client = self._eleve_uuid(eleve_id)
        payload = dict(data)
        payload.pop("photo", None)
        payload["eleve_uuid"] = uuid_client
        classe_nom = self._classe_nom(data.get("classe_id"))
        if classe_nom:
            payload["classe_nom"] = classe_nom
        set_clause = ", ".join(f"{c} = ?" for c in cols)
        self._route_write("PUT", f"/modifierEleve/{eleve_id}", payload,
                          db.execute,
                          f"UPDATE eleves SET {set_clause} WHERE id = ?",
                          tuple_vals)

    def delete_eleve(self, eleve_id):
        uuid_client = self._eleve_uuid(eleve_id)
        payload = {"eleve_uuid": uuid_client}
        with db.transaction() as txn:
            txn.execute("DELETE FROM notes WHERE eleve_id = ?", (eleve_id,))
            txn.execute("DELETE FROM presences WHERE eleve_id = ?", (eleve_id,))
            txn.execute("DELETE FROM paiements WHERE eleve_id = ?", (eleve_id,))
            txn.execute("DELETE FROM eleves WHERE id = ?", (eleve_id,))
        self._route_write("DELETE", f"/eleve/{eleve_id}/notes", payload,
                          lambda *a, **kw: None)
        self._route_write("DELETE", f"/eleve/{eleve_id}/presences", payload,
                          lambda *a, **kw: None)
        self._route_write("DELETE", f"/eleve/{eleve_id}/paiements", payload,
                          lambda *a, **kw: None)
        self._route_write("DELETE", f"/eleve/{eleve_id}", payload,
                          lambda *a, **kw: None)

    def _eleve_uuid(self, eleve_id):
        row = db.query_one("SELECT uuid_client FROM eleves WHERE id = ?", (eleve_id,))
        return row["uuid_client"] if row else None

    def _classe_nom(self, classe_id):
        if not classe_id:
            return None
        row = db.query_one("SELECT nom FROM classes WHERE id = ?", (classe_id,))
        return row["nom"] if row else None

    def next_matricule(self):
        year = __import__("datetime").date.today().year
        prefix = f"ELEV{year}"
        conn = db.connect()
        try:
            cur = conn.execute(
                "SELECT MAX(CAST(SUBSTR(matricule, ?) AS INTEGER)) AS max_num FROM eleves WHERE matricule LIKE ?",
                (len(prefix) + 1, f"{prefix}%"))
            row = cur.fetchone()
            num = (row["max_num"] or 0) + 1
            return f"{prefix}{num:04d}"
        finally:
            conn.close()
