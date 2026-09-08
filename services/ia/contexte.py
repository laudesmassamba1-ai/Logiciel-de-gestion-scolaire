"""Memoire conversationnelle de Charo : donne a l'assistante une notion de
« fil de discussion » comme les grands assistants de chat.

Ce que le module sait faire :
- retenir les entites des derniers echanges (classe, eleve, periode, sujet) ;
- resoudre les ANAPHORES courtes du francais parle :
    « combien d'eleves en 6eme ? » puis « et en cm2 ? »
    « moyenne de Mambou »          puis « et ses paiements ? »
- borner l'historique (fenetre glissante) pour rester leger.
"""

import re

from services.ia.langue import normaliser

_RE_CLASSE = re.compile(
    r"\b(\d{1,2}\s?(?:eme|ere|nd|nde)|cm\d|cp|ce\d|maternelle|"
    r"petite section|moyenne section|grande section|lycee|college)\b")
_RE_INTERROGATIVE = re.compile(
    r"^(combien|quelle?s?|quel?s?|qui|ouvre|moyenne|solde|masse)")
_SUIVIS_ELEVE = {
    "sa moyenne": "moyenne de {eleve}",
    "ses moyennes": "moyennes de {eleve}",
    "ses paiements": "combien a paye {eleve}",
    "ses absences": "absences de {eleve}",
    "sa fiche": "fiche de {eleve}",
}
_MAX_HISTORIQUE = 10


class ContexteConversation:

    def __init__(self):
        self.historique = []       # [(question normalisee, classe, eleve)]
        self.derniere_classe = None
        self.dernier_eleve = None  # libelle
        self.derniere_periode = None

    # -- enregistrement --------------------------------------------------

    def noter(self, question_t, classe=None, eleve=None, periode=None):
        """Appelle APRES une reponse utile : memorise tour + entites."""
        if classe is None:
            m = _RE_CLASSE.search(question_t)
            classe = m.group(1) if m else None
        self.derniere_classe = classe or self.derniere_classe
        if eleve:
            self.dernier_eleve = eleve
        if periode:
            self.derniere_periode = periode
        self.historique.append((question_t, self.derniere_classe,
                                self.dernier_eleve))
        if len(self.historique) > _MAX_HISTORIQUE:
            self.historique.pop(0)

    def vider(self):
        self.historique.clear()
        self.derniere_classe = None
        self.dernier_eleve = None
        self.derniere_periode = None

    # -- resolution d'anaphores ------------------------------------------

    def reformuler(self, t):
        """Si t est un suivi (« et en cm2 ? », « et lui ? »...), renvoie la
        question complete reconstruite. Sinon None."""
        if not t or not self.historique:
            return None
        if not re.match(r"^(et\b|lui\b|elle\b|sa |ses |son )", t):
            return None
        if len(t.split()) > 6:
            return None
        question_prec = next(
            (q for q, _c, _e in reversed(self.historique)
             if _RE_INTERROGATIVE.match(q)), None)
        if question_prec is None:
            return None

        fragment = t[3:].strip()
        fragment = re.sub(r"[?!.;:, ]+$", "", fragment) if t.startswith("et ") else t.strip()

        # 1) « et en cm2 ? » : on remplace la classe dans la question precedente
        classe_frag = _RE_CLASSE.search(fragment)
        if classe_frag:
            nouvelle_classe = classe_frag.group(1)
            if _RE_CLASSE.search(question_prec):
                return _RE_CLASSE.sub(nouvelle_classe, question_prec, count=1)
            if _RE_INTERROGATIVE.match(question_prec) and "classe" not in \
                    question_prec:
                return f"{question_prec} en {nouvelle_classe}"

        # 2) « et les filles ? » / « et les garcons ? »
        genre = {"les filles": "filles", "les garcons": "garcons",
                 "les garçons": "garcons"}.get(fragment)
        if genre and "combien" in question_prec:
            classe = self.derniere_classe or ""
            suffixe = f" en {classe}" if classe else ""
            return f"combien de {genre}{suffixe}"

        # 3) « et sa moyenne ? » : reutilise le dernier eleve connu
        cle = re.sub(r"[?!,.;: ]+$", "",
                     re.sub(r"^(et\s+)", "", fragment)).strip()
        gabarit = _SUIVIS_ELEVE.get(cle)
        if gabarit and self.dernier_eleve:
            return gabarit.format(eleve=self.dernier_eleve)

        return None


def extraire_classe(t):
    m = _RE_CLASSE.search(t)
    return normaliser(m.group(1)) if m else None
