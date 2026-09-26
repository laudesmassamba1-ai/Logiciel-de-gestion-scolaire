"""Routeur d'intentions declaratif de Charo (phase P1 du projet v2).

Au lieu d'essayer dans un ORDRE FIXE une douzaine de handlers metier, on
declare ce que chaque handler sait repondre, avec ses mots-cles ; le
routeur score la question et choisit le handler le plus pertinent.

Principes (voir docs/PROJET_CHARO_IA_LOCALE.md, pilier 1) :
  * aucun modele, aucune dependance : mots-cles + regex + ponderation ;
  * degradee gracieuse : si le handler choisi renvoie None, l'appelant
    rebascule sur l'ancien ordre fixe (donc aucune regression possible) ;
  * introspection : `expliquer()` renvoie le detail du classement, ce qui
    alimente la trace d'apprentissage et les tests.

Ce module n'importe RIEN du moteur (assistant_ia) : il ne contient que
des donnees declaratives et du scoring, donc il reste testable isolement.
"""

import re
from dataclasses import dataclass

from services.ia.langue import normaliser


# --------------------------------------------------------------------------
# Seuils
# --------------------------------------------------------------------------

#: En dessous de ce score, aucune intention n'est retenue : on laisse
#: l'ancien parcours (memoire, corpus, web, LLM) faire son travail.
SEUIL_INTENTION = 0.45

#: A ce score, la question est explicite : on peut court-circuiter les
#: handlers de priorite superieure (ils n'auraient pas la bonne reponse).
SEUIL_CONFIANT = 0.80

# Bareme de scoring (repris tel quel par `Intention.scorer`) :
#   1 cle trouvee          -> 0.60   (« moyenne generale » : le mot rare)
#   2 cles ou plus         -> 0.80
#   2 mots d'appoint       -> 0.50   (« frais + scolarite »)
#   3 mots d'appoint       -> 0.60
#   1 seul mot d'appoint   -> 0.30   (trop vague : sous le seuil, repli)
#   expression reguliere   -> +0.25  (« etat de la caisse » : sans ambiguite)
# Le resultat est multiplie par le poids de l'intention puis borne a 1.0.
BAREME_CLE_UNIQUE = 0.60
BAREME_CLES_MULTIPLES = 0.80
BAREME_DEUX_MOTS = 0.50
BAREME_TROIS_MOTS = 0.60
BAREME_MOT_UNIQUE = 0.30
BONUS_REGEX = 0.25


def _mot_present(texte, mot):
    """Presence en mot entier : « moyenne » ne doit pas reagir a
    « moyenneponderee » ni « superieur » a « super »."""
    return re.search(rf"\b{re.escape(mot)}\b", texte) is not None


@dataclass(frozen=True)
class Intention:
    """Une intention declarant ce que sait faire un handler.

    cles      : mots rares et discriminants ; un seul suffit a qualifier
                l'intention (0.60) ;
    mots      : mots d'appoint ; il en faut deux pour qualifier (0.50) ;
    expressions : regex additionnelles, plus fortes qu'un mot-cle (+0.25) ;
    poids     : multiplicateur de score (une intention prioritaire comme la
                moyenne generale domine une intention generique) ;
    handler   : nom de la methode de l'assistant a appeler ;
    exige_donnees : False pour une intention qui repond meme sans lecture
                de base (utilise par les diagnoseurs de donnees) ;
    """

    nom: str
    cles: tuple = ()
    mots: tuple = ()
    synonymes: tuple = ()
    expressions: tuple = ()
    poids: float = 1.0
    handler: str = ""
    exige_donnees: bool = True
    exemple: str = ""

    @property
    def motifs(self):
        """Tous les mots declares (cles + mots + synonymes)."""
        return tuple(self.cles) + tuple(self.mots) + tuple(self.synonymes)

    def scorer(self, question):
        """Score de l'intention pour cette question, borne a 1.0.

        Le bareme est explicite (constantes ci-dessus) pour qu'un
        classificateur reste stable : ajouter un mot-cle ne peut pas
        « demonter » une intention deja bien notee.
        """
        question = normaliser(question)
        cles = [c for c in self.cles if _mot_present(question, c)]
        mots = [m for m in self.mots if _mot_present(question, m)]
        mots += [s for s in self.synonymes if _mot_present(question, s)]
        regex_ok = any(re.search(p, question) for p in self.expressions)
        if cles:
            base = BAREME_CLE_UNIQUE if len(cles) == 1 else BAREME_CLES_MULTIPLES
        elif len(mots) >= 3:
            base = BAREME_TROIS_MOTS
        elif len(mots) == 2:
            base = BAREME_DEUX_MOTS
        elif mots or regex_ok:
            base = BAREME_MOT_UNIQUE
        else:
            return 0.0
        score = base + (BONUS_REGEX if regex_ok else 0.0)
        return min(1.0, score * self.poids)


#: Registre des intentions metier. Volontairement sobre : on declare ce que
#: les handlers existants savent faire, on n'ecrit aucun nouveau handler.
REGISTRE = (
    Intention(
        nom="moyenne_generale",
        cles=("generale", "generaux", "generales"),
        mots=("moyenne", "moy"),
        expressions=(r"moyenne g[eé]n[eé]rale",
                     r"quelle est sa moyenne",
                     r"moyenne de .* [eé]l[eè]ve"),
        poids=1.15,
        handler="_q_moyenne_generale",
        exemple="Quelle est la moyenne generale de Mbemba ?",
    ),
    Intention(
        nom="classement",
        cles=("classement", "rang", "rangs", "position", "palmares"),
        mots=("classer", "premier", "derniere", "dernier"),
        expressions=(r"classement (de|du|pour)",
                     r"quel est (son|le|la) (rang|classement|position)"),
        poids=1.05,
        handler="_q_classement",
        exemple="Quel est le classement de la classe 6eB ?",
    ),
    Intention(
        nom="paiements_eleve",
        cles=("paye", "paye", "regle", "reglee", "regles", "versement",
              "versements", "dette", "doit"),
        mots=("paiement", "paiements", "payer", "solde", "reste"),
        expressions=(r"(a|est|il) .*(regle|pay[eé]|vers)",
                     r"reste (a|du) payer",
                     r"qu[a']il doit",
                     r"a paye"),
        poids=1.05,
        handler="_q_paiements_eleve",
        exemple="Est-ce que Mbemba a paye sa scolarite ?",
    ),
    Intention(
        nom="absences",
        cles=("absence", "absences", "absent", "absente", "retards",
              "retard"),
        mots=("presence", "presences", "present", "presents"),
        expressions=(r"combien (d['’]?)?(il y a )?.*absences",
                     r"taux de presence",
                     r"absent(e)?s?"),
        poids=1.0,
        handler="_q_absences",
        exemple="Combien d'absences a Mbemba ?",
    ),
    Intention(
        nom="moyennes",
        cles=("moyennes", "notes de", "moyenne de"),
        mots=("moyenne", "note", "notes", "moy", "bulletin"),
        expressions=(r"moyennes? (de|du|par) ",
                     r"quelles? (sont les )?moyennes",
                     r"notes? de .*classe"),
        poids=0.95,
        handler="_q_moyennes",
        exemple="Quelles sont les moyennes de la classe de 6eB ?",
    ),
    Intention(
        nom="tarifs_classe",
        cles=("tarif", "tarifs", "frais", "coute", "coutent"),
        mots=("scolarite", "inscription", "cantine", "transport", "montant",
              "tenue", "tenues"),
        expressions=(r"(quel|quels) (tarif|frais)",
                     r"combien (ca coute|co[uû]te|tient)",
                     r"(quel|quels) frais"),
        poids=0.90,
        handler="_q_tarifs_classe",
        exemple="Quels sont les frais de la classe de 6eB ?",
    ),
    Intention(
        nom="caisse",
        cles=("caisse", "tresorerie"),
        mots=("recette", "recettes", "depense", "depenses", "solde",
              "encaisse", "encaissement"),
        expressions=(r"(etat|recettes?) (de|de la) caisse",
                     r"combien (avons|reste).*caisse",
                     r"solde de la caisse"),
        poids=0.90,
        handler="_q_caisse",
        exemple="Quel est l'etat de la caisse ?",
    ),
    Intention(
        nom="personnel",
        cles=("professeur", "prof", "profs", "enseignant", "enseignante",
              "professeure"),
        mots=("personnel", "titulaire", "maitre", "maitre", "formateur"),
        expressions=(r"(quel|qui|quels|quelles) .*prof",
                     r"professeur de .*classe",
                     r"qui (enseigne|fait) .*classe"),
        poids=0.90,
        handler="_q_personnel",
        exemple="Qui est le professeur de 6eB ?",
    ),
    Intention(
        nom="annee_active",
        cles=("annee scolaire", "trimestre", "trimestres", "rentree",
              "vacances", "periodes"),
        mots=("annee", "periode", "en cours", "calendrier", "jour"),
        expressions=(r"(quelle|quel) .*(annee|trimestre|periode)",
                     r"en cours d['’]? ?annee",
                     r"on est (en|au) (quel|trimestre)"),
        poids=0.85,
        handler="_q_annee_active",
        exemple="Quel trimestre sommes-nous ?",
    ),
    Intention(
        nom="fiche_eleve",
        cles=("fiche", "dossier", "etat civil", "parents", "parent", "tuteur"),
        mots=("infos", "profil", "coordonnees", "informations", "adresse"),
        expressions=(r"(fiche|dossier) (de|du)",
                     r"informations sur .*[eé]l[eè]ve",
                     r"(quel|quels) (sont les )?parents"),
        poids=0.90,
        handler="_q_fiche_eleve",
        exemple="Montre-moi la fiche de Mbemba.",
    ),
    Intention(
        nom="effectifs",
        cles=("effectif", "effectifs", "inscrits", "total"),
        mots=("combien", "nombre", "classe", "cycle", "niveau"),
        expressions=(r"combien d['’]? ?(eleves?|etudiants?)",
                     r"nombre d['’]? ?(eleves?|etudiants?)",
                     r"effectif (de|du|par)",
                     r"combien .* (classe|cycle|niveau)"),
        poids=0.85,
        handler="_q_effectifs",
        exemple="Combien d'eleves en 6eB ?",
    ),
    Intention(
        nom="graphe",
        cles=("liens", "lien", "relations", "relation", "chemin", "connecte",
              "proches", "proche", "lies", "lie"),
        mots=("rapport", "connections", "voisins"),
        expressions=(r"(quel|quels) (lien|liens|rapport|relation)",
                     r"est (il )?connecte",
                     r"chemin entre",
                     r"li[eé] (a|avec|par)"),
        poids=0.80,
        handler="_q_graphe",
        exemple="Quels sont les liens entre Mbemba et 6eB ?",
    ),
)


class RouteurIntentions:
    """Classement des intentions pour une question (calcul pur, sans effet)."""

    def __init__(self, intentions=REGISTRE):
        self._intentions = tuple(intentions)

    @property
    def intentions(self):
        return self._intentions

    def classer(self, question):
        """Toutes les intentions notees, de la meilleure a la moins bonne.

        Renvoie [(Intention, score), ...] (les scores nuls sont exclus)."""
        texte = normaliser(question)
        notes = [(i, i.scorer(texte)) for i in self._intentions]
        notes = [(i, s) for i, s in notes if s > 0.0]
        notes.sort(key=lambda paire: (-paire[1], paire[0].nom))
        return notes

    def resoudre(self, question, seuil=SEUIL_INTENTION):
        """Meilleure intention au-dessus du seuil.

        Renvoie (Intention|None, score, classement). Le classement complet
        est toujours fourni : c'est ce que consomme `expliquer()` (trace
        d'apprentissage) et les tests. A score egal, l'intention declaree en
        premier l'emporte (tie-break nominal, pas alphabetique)."""
        classement = self.classer(question)
        if not classement:
            return None, 0.0, classement
        meilleure, score = classement[0]
        if score < seuil:
            return None, score, classement
        rang = {i.nom: n for n, i in enumerate(self._intentions)}
        for autre, autre_score in classement[1:]:
            if abs(autre_score - score) < 1e-9 and rang[autre.nom] < rang[meilleure.nom]:
                meilleure, score = autre, autre_score
                break
        return meilleure, score, classement

    def expliquer(self, question, seuil=SEUIL_INTENTION):
        """Trace lisible du classement (debug, tests, journal)."""
        meilleure, score, classement = self.resoudre(question, seuil)
        if meilleure is not None:
            lignes = [f"'{question}' -> {meilleure.nom} ({score:.2f})"]
        else:
            lignes = [f"'{question}' -> aucune intention"]
        for intention, note in classement[:4]:
            lignes.append(f"   {intention.nom}: {note:.2f}"
                          f" (handler {intention.handler})")
        return "\n".join(lignes)


#: Instance partagee (registre immuable, aucun etat).
_ROUTEUR = RouteurIntentions()


def get_routeur():
    return _ROUTEUR
