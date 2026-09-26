"""Moteur d'apprentissage autonome de Charo (session 2026-09-09).

Objectif : tendre vers un assistant qui « apprend, raisonne, s'ameliore et
se stocke tout seul », sans aucune dependance externe ni GPU.

4 mecanismes complementaires :

1. JOURNAL — chaque tour de conversation (question -> reponse + source) est
   trace dans une table `ia_journal` (deroulement inchange, purge auto des
   vieux tours).

2. FEEDBACK — l'utilisateur note les reponses (+/-). La table `ia_feedback`
   enregistre l'avis. Les entres de `ia_memoire` associees voient leur score
   de confiance ajuste : les bonnes reponses sont renforcees (plus souvent
   rejuees), les mauvaises sont degradees puis automatiquement luees lors de
   l'entrainement.

3. RENFORCEMENT — chaque rejeu d'une memoire (usage +1) la renforce
   discretement (score + epsilon) et horodate son dernier usage.

4. AUTO-AMELIORATION (entrainement) — pass periodique, sans cout perceptible :
   - consolidation : deux questions quasi identiques sont fusionnees en
     conservant la plus utilisee (dedoublonnage) ;
   - nettoyage : les appels sans usage et tres mal notes sont supprimes ;
   - purge du journal (limite haute) ;
   - metriques remises a jour pour le pilotage (« je m'ameliore seule »).

Toutes les tables sont creees a la volee (CREATE IF NOT EXISTS) et la table
`ia_memoire` existante est migree en douceur (ALTER TABLE / PRAGMA) pour ne
rien casser des base deja en production.
"""

import datetime
import time
import unicodedata

from difflib import SequenceMatcher

from database import db

_LIMITE_JOURNAL = 1500
_COOLDOWN_ENTRAINEMENT = 600.0
_SEUIL_FUSION = 0.90
_SEUIL_SUPPRESSION = 0.25
_MAX_USAGE_SUPPRESSION = 2
_SEUIL_QUESTION_FREQUENTE = 3


def _nettoyer(texte):
    """Normalisation sommaire (accents/ponctuation) pour comparer questions."""
    if not texte:
        return ""
    t = unicodedata.normalize("NFD", texte or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return " ".join(t.split())


class MoteurApprentissage:
    """Stocke les traces, gere les retours utilisateur et l'entrainement."""

    def __init__(self):
        self._tables_preres = False

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def ensure_tables(self):
        if self._tables_preres:
            return
        db.execute("""CREATE TABLE IF NOT EXISTS ia_memoire (
                          id          INTEGER PRIMARY KEY AUTOINCREMENT,
                          type        TEXT NOT NULL DEFAULT 'qa',
                          question    TEXT NOT NULL,
                          reponse     TEXT NOT NULL,
                          usage       INTEGER NOT NULL DEFAULT 0,
                          appris_le   TEXT NOT NULL DEFAULT
                                      (datetime('now','localtime')),
                          score       REAL NOT NULL DEFAULT 1.0,
                          source      TEXT NOT NULL DEFAULT 'manuel',
                          dernier_usage TEXT,
                          utilisateur_id INTEGER)""")
        db.execute("""CREATE TABLE IF NOT EXISTS ia_feedback (
                          id       INTEGER PRIMARY KEY AUTOINCREMENT,
                          question TEXT NOT NULL,
                          reponse  TEXT NOT NULL,
                          note     INTEGER NOT NULL,
                          motif    TEXT,
                          date     TEXT NOT NULL DEFAULT
                                   (datetime('now','localtime')))""")
        db.execute("""CREATE TABLE IF NOT EXISTS ia_journal (
                          id       INTEGER PRIMARY KEY AUTOINCREMENT,
                          question TEXT NOT NULL,
                          reponse  TEXT NOT NULL,
                          source   TEXT NOT NULL DEFAULT 'moteur',
                          date     TEXT NOT NULL DEFAULT
                                   (datetime('now','localtime')))""")
        db.execute("""CREATE TABLE IF NOT EXISTS ia_metriques (
                          cle    TEXT PRIMARY KEY,
                          valeur REAL NOT NULL DEFAULT 0)""")
        self._migrer_memoire()
        self._tables_preres = True

    def _migrer_memoire(self):
        """Ajoute les nouvelles colonnes a une table ia_memoire existante."""
        colonnes = {r["name"] for r in db.query("PRAGMA table_info(ia_memoire)")}
        if "score" not in colonnes:
            db.execute("ALTER TABLE ia_memoire ADD COLUMN score REAL NOT NULL DEFAULT 1.0")
        if "source" not in colonnes:
            db.execute("ALTER TABLE ia_memoire ADD COLUMN source TEXT NOT NULL DEFAULT 'manuel'")
        if "dernier_usage" not in colonnes:
            db.execute("ALTER TABLE ia_memoire ADD COLUMN dernier_usage TEXT")
        if "utilisateur_id" not in colonnes:
            db.execute("ALTER TABLE ia_memoire ADD COLUMN utilisateur_id INTEGER")

    # ------------------------------------------------------------------
    # Metriques
    # ------------------------------------------------------------------

    def _metrique(self, cle, delta=1.0):
        self.ensure_tables()
        db.execute(
            "INSERT INTO ia_metriques (cle, valeur) VALUES (?, ?) "
            "ON CONFLICT(cle) DO UPDATE SET valeur = valeur + excluded.valeur",
            (cle, delta))

    def _metrique_lire(self, cle):
        self.ensure_tables()
        ligne = db.query_one("SELECT valeur FROM ia_metriques WHERE cle = ?",
                             (cle,))
        return ligne["valeur"] if ligne else 0.0

    # ------------------------------------------------------------------
    # Journalisation
    # ------------------------------------------------------------------

    def consigner(self, question, reponse, source="moteur"):
        """Trace un tour de conversation (source : memoire/llm/corpus/...)."""
        self.ensure_tables()
        if question is None or not (question or "").strip():
            return
        db.execute(
            "INSERT INTO ia_journal (question, reponse, source) VALUES (?, ?, ?)",
            (str(question)[:300], str(reponse)[:2000], source or "moteur"))
        self._metrique("total_questions")
        self._purger_journal()

    def _purger_journal(self):
        db.execute(
            "DELETE FROM ia_journal WHERE id NOT IN "
            "(SELECT id FROM ia_journal ORDER BY id DESC LIMIT ?)",
            (_LIMITE_JOURNAL,))

    # ------------------------------------------------------------------
    # Feedback + renforcement
    # ------------------------------------------------------------------

    def vu_memoire(self, ligne):
        """Renforce discretement un rejeu de memoire (usage + 1)."""
        self.ensure_tables()
        now = datetime.datetime.now().isoformat(timespec="seconds")
        db.execute(
            "UPDATE ia_memoire SET usage = usage + 1, "
            "score = MIN(3.0, score + 0.05), dernier_usage = ? WHERE id = ?",
            (now, ligne))

    def noter(self, question, reponse, note, motif=None):
        """Enregistre un retour utilisateur (+1 bon / -1 mauvais).

        Retourne le nombre d'entrees `ia_memoire` dont le score est ajuste.
        """
        self.ensure_tables()
        if note == 0:
            return 0
        db.execute(
            "INSERT INTO ia_feedback (question, reponse, note, motif) "
            "VALUES (?, ?, ?, ?)",
            (str(question or "")[:300], str(reponse or "")[:2000],
             int(note), (motif or "")[:500]))
        self._metrique("feedback_pos" if note > 0 else "feedback_neg")

        ajustees = 0
        q_n = _nettoyer(question)
        r_n = _nettoyer(reponse)
        for ligne in db.query("SELECT * FROM ia_memoire"):
            lq = _nettoyer(ligne["question"])
            lr = _nettoyer(ligne["reponse"])
            sim_q = SequenceMatcher(None, lq, q_n).ratio() if q_n and lq else 0.0
            sim_r = SequenceMatcher(None, lr, r_n).ratio() if r_n and lr else 0.0
            inclusions = (r_n and lr and (lr in r_n or r_n in lr))
            if sim_q >= 0.6 or sim_r >= 0.6 or inclusions:
                delta = 0.35 if note > 0 else -0.45
                nouveau = max(0.05, min(3.0, float(ligne["score"]) + delta))
                db.execute("UPDATE ia_memoire SET score = ? WHERE id = ?",
                           (nouveau, ligne["id"]))
                ajustees += 1
        return ajustees

    # ------------------------------------------------------------------
    # Auto-amelioration
    # ------------------------------------------------------------------

    def ameliorer(self, force=False):
        """Pass d'entrainement : fusion des doublons, nettoyage, purge,
        et auto-apprentissage des questions frequentes.

        Automatiquement mis en veille (cooldown court de 10 min) sauf si
        force=True.
        Retourne un rapport {fusionne, retires, appris, memoire, journal}.
        """
        self.ensure_tables()
        if not force:
            dernier = self._metrique_lire("dernier_entrainement")
            if dernier and time.time() - dernier < _COOLDOWN_ENTRAINEMENT:
                return {"fusionne": 0, "retires": 0, "appris": 0,
                        "rejouee": 0,
                        "memoire": self._taille_memoire(),
                        "journal": self._taille_journal(), "publicite": False}

        fusionnes = self._consolider_memoire()
        retires = self._supprimer_faibles()
        appris = self._apprendre_questions_frequentes()
        self._purger_journal()

        maintenant = time.time()
        db.execute(
            "INSERT INTO ia_metriques (cle, valeur) VALUES "
            "('dernier_entrainement', ?) "
            "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
            (maintenant,))
        self._metrique("entrainements")

        return {"fusionne": fusionnes, "retires": retires, "appris": appris,
                "rejouee": 0,
                "memoire": self._taille_memoire(),
                "journal": self._taille_journal(), "publicite": True}

    def _apprendre_questions_frequentes(self):
        """Apprend tout seul les questions qui reviennent regulierement.

        Principe « l'IA apprend toute seule » : une question posee au
        moins _SEUIL_QUESTION_FREQUENTE fois provient d'un vrai besoin
        metier — il serait dommage de n'avoir jamais de reponse. Le moteur
        transforme alors la meilleure reponse du journal (la plus stable,
        hors messages de secours) en souvenir durable `ia_memoire`
        (source="auto"), rejouable des la session suivante.

        Inoffensif et borne : aucune question unique n'est apprise ; les
        souvenirs ainsi crees peuvent etre ajustes par le feedback puis
        supprimes par l'entrainement s'ils s'averent mauvais."""
        self.ensure_tables()
        deja = {_nettoyer(r["question"])
                for r in db.query("SELECT question FROM ia_memoire")}
        candidates = db.query(
            "SELECT question, reponse, source, COUNT(*) AS c "
            "FROM ia_journal GROUP BY question, reponse HAVING c >= ?",
            (_SEUIL_QUESTION_FREQUENTE,))
        appris = 0
        for ligne in candidates:
            q = _nettoyer(ligne["question"])
            if not q or q in deja:
                continue
            reponse = (ligne["reponse"] or "").strip()
            if not self._est_bonne_reponse(reponse):
                continue
            db.execute(
                "INSERT INTO ia_memoire (type, question, reponse, source, "
                "score) VALUES ('qa', ?, ?, 'auto', 0.6)",
                (ligne["question"][:200], reponse[:2000]))
            deja.add(q)
            appris += 1
        if appris:
            self._metrique("auto_apprentissages", appris)
        return appris

    @staticmethod
    def _est_bonne_reponse(reponse):
        """Considere qu'une reponse de secours n'est pas a retenir."""
        if not reponse or len(reponse) < 10:
            return False
        rl = reponse.lower()
        for marqueur in ("n'ai pas", "pas la reponse", "pas compris",
                         "proposez", "proposons", "apprends-moi",
                         "essayons", "je peux vous aider"):
            if marqueur in rl:
                return False
        return True

    def _consolider_memoire(self):
        """Fusionne les questions quasi identiques (garder la plus utilisee)."""
        lignes = db.query("SELECT id, question, usage FROM ia_memoire")
        conserver = set()
        supprimer = set()
        for i, a in enumerate(lignes):
            if a["id"] in supprimer:
                continue
            for b in lignes[i + 1:]:
                if b["id"] in supprimer:
                    continue
                ra = SequenceMatcher(
                    None, _nettoyer(a["question"]), _nettoyer(b["question"]))\
                    .ratio()
                if ra >= _SEUIL_FUSION and abs(a["usage"] - b["usage"]) < 6:
                    conserver.add(a["id"])
                    supprimer.add(b["id"])
        if supprimer:
            for ident in supprimer:
                db.execute("DELETE FROM ia_memoire WHERE id = ?", (ident,))
        return len(supprimer)

    def _supprimer_faibles(self):
        """Supprime les apprentissages jamais rejoues et tres mal notes."""
        retour = db.query(
            "SELECT id FROM ia_memoire "
            "WHERE usage <= ? AND score < ?",
            (_MAX_USAGE_SUPPRESSION, _SEUIL_SUPPRESSION))
        for ligne in retour:
            db.execute("DELETE FROM ia_memoire WHERE id = ?", (ligne["id"],))
        return len(retour)

    # ------------------------------------------------------------------
    # Statistiques
    # ------------------------------------------------------------------

    def statistiques(self):
        self.ensure_tables()
        taille_mem = self._taille_memoire()
        usage_total = db.query_one(
            "SELECT COALESCE(SUM(usage), 0) AS s FROM ia_memoire")
        return {
            "total_questions": int(self._metrique_lire("total_questions")),
            "apprentissages": taille_mem,
            "rejeux": int(usage_total["s"] if usage_total else 0),
            "feedback_pos": int(self._metrique_lire("feedback_pos")),
            "feedback_neg": int(self._metrique_lire("feedback_neg")),
            "entrainements": int(self._metrique_lire("entrainements")),
            "auto_apprentissages": int(
                self._metrique_lire("auto_apprentissages")),
            "journal": self._taille_journal(),
        }

    def _taille_memoire(self):
        ligne = db.query_one("SELECT COUNT(*) AS c FROM ia_memoire")
        return ligne["c"] if ligne else 0

    def _taille_journal(self):
        ligne = db.query_one("SELECT COUNT(*) AS c FROM ia_journal")
        return ligne["c"] if ligne else 0