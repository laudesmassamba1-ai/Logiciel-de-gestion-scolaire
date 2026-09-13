"""Assistante locale « Charo » de l'application Gestion Scolaire.

100 % Python standard : aucun modele a telecharger, aucune carte graphique,
aucune connexion Internet requise. Elle tourne instantanement sur n'importe
quel PC, meme sans GPU.

Trois couches cooperent :

1. COMPRENDRE ET AGIR — moteur d'intentions (mots-cles ponderes, extraction
   d'entites floue par SequenceMatcher) branche sur les repositories :
   repond avec les vraies donnees, calcule (moyennes ponderees, soldes,
   arithmetique), ouvre les pages, cree des entites avec confirmation,
   pilote la synchronisation multi-postes.

2. LIRE LES DONNEES — l'assistant indexe le contenu de la base (eleves,
   classes, transactions, tarifs, personnel) dans un index TF-IDF local et
   retrouve par similitude cosinus le document pertinent quand une question
   libre est posee.

3. APPRENDRE — memoire persistante en SQLite (table ia_memoire) :
   « retiens que ... », « quand je dis X reponds Y », ou enseignement guide
   apres une question sans reponse. Ce qui est appris est rejoue lors des
   sessions suivantes et enrichit les reponses (« oublie » pour effacer).

Le moteur ne touche jamais au reseau ni a l'affichage : il renvoie des
reponses structurees {"texte", "action", "choix"} que l'interface execute.
"""

import datetime
import math
import re
import time
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

from core.config import PERIODES, ROLE_LABELS
from database import db
from repositories import repos
from services.ia.contexte import ContexteConversation
from services.ia.graphe import GrapheEcole
from services.ia.langue import corriger_phrase, normaliser as normaliser_ia, similarite
from services.ia import maths as ia_maths
from services.ia.llm_backend import get_backend
from services.ia.apprentissage import MoteurApprentissage

NOM_ASSISTANT = "Charo"

_LLM = None


def _llm_disponible():
    global _LLM
    if _LLM is None:
        _LLM = get_backend()
    return _LLM.disponible()

# Vocabulaire de base de la correction orthographique (complete par les
# noms reels de la base : classes, eleves, matieres...). Un mot absent du
# vocabulaire et sans proche voisin n'est JAMAIS modifie.
_VOCABULAIRE_DE_BASE = {
    "combien", "eleve", "eleves", "eleves", "classe", "classes", "moyenne",
    "moyennes", "caisse", "solde", "paiement", "paiements", "paye", "payer",
    "absent", "absente", "absents", "absences", "absence", "tarif", "tarifs",
    "masse", "salariale", "annee", "annees", "active", "actif", "fiche",
    "effectif", "effectifs", "cycle", "cycles", "matiere", "matieres",
    "creer", "cree", "inscrit", "inscrire", "inscription", "ouvre",
    "ouvrir", "montre", "liste", "total", "quelle", "quels", "qui",
    "comment", "aide", "manuel", "synchronise", "serveur", "poste",
    "connexion", "entree", "sortie", "transaction", "transactions",
    "enseignant", "enseignants", "professeur", "personnel", "bulletin",
    "bulletins", "notes", "note", "devoir", "composition", "periode",
    "trimestre", "semestre", "filles", "garcons", "retiens", "oublie",
    "memoire", "apprends", "apprentissage", "lien", "relation", "chemin",
    "structure", "organisation", "ecole", "aujourdhui", "hier", "demain",
    "moyenne", "generale", "resultats", "classement", "premier", "dernier",
    "redoublant", "matricule", "naissance", "tuteur", "pere", "mere",
    "planning", "emploi", "temps", "programme", "programmes", "coefficient",
    "capacite", "salle", "titulaire", "statut", "montant", "fcfa",
    "scolaire", "scolarite", "salaire", "salaires", "salariales",
    "bonjour", "salut", "bonsoir", "au revoir", "revoir", "merci",
    "super", "genial", "top", "bye", "a bientot", "quoi",
}

_SEUIL_MEMOIRE = 0.28
_SEUIL_CORPUS = 0.32

_MOTS_VIDES = {
    "eleve", "eleves", "l eleve", "fiche", "de", "du", "des", "le", "la",
    "les", "qui", "est", "info", "infos", "information", "informations",
    "cherche", "trouver", "trouve", "montre", "moi", "sur", "un", "une",
    "et", "solde", "paiement", "paiements", "notes", "note", "moyenne",
    "combien", "nombre", "total", "effectif", "classe", "classes",
    "a", "au", "aux", "en", "dans", "pour", "par", "que", "quel", "quelle",
    "quels", "quelles", "ce", "cet", "cette", "donne", "dis", "svp",
    "peux", "tu", "je", "voudrais", "veux", "il", "elle", "on", "nous",
    "vous", "son", "sa", "ses", "leur", "leurs", "y", "s", "plus", "moins",
}


# --------------------------------------------------------------------------
# Normalisation et formatage
# --------------------------------------------------------------------------

def normaliser(texte):
    """Minuscules + suppression des accents + apostrophes -> espaces."""
    t = unicodedata.normalize("NFD", texte or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"['\u2019`\"]", " ", t)
    t = re.sub(r"[^a-z0-9\s%+\-*/().,:<=>]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def formater_fcfa(montant):
    try:
        v = float(montant)
    except (TypeError, ValueError):
        return "0 FCFA"
    if abs(v - int(v)) < 0.005:
        return f"{int(v):,}".replace(",", " ") + " FCFA"
    return f"{v:,.2f}".replace(",", " ") + " FCFA"


def formater_date(iso):
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin", "Juillet",
            "Aout", "Septembre", "Octobre", "Novembre", "Decembre"]
    try:
        d = datetime.date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)
    return f"{jours[d.weekday()]} {d.day} {mois[d.month - 1]} {d.year}"


def appreciation(moyenne):
    from services.appreciations import appreciation as _app
    return _app(moyenne)


def _contient(texte, *mots):
    return all(m in texte for m in mots)


def _contient_un(texte, *mots):
    return any(m in texte for m in mots)


def _oui(texte):
    if _non(texte):
        return False
    return _contient_un(texte, "oui", "confirm", "valide", "vas y", "va y",
                        "yes") or texte in ("ok", "ok ", "d accord", "daccord",
                                            "c est parti", "go")


def _non(texte):
    return _contient_un(texte, "annuler", "annule", "abandon", "stop") \
        or texte in ("non", "no", "nan")


def _mot_present(texte, *mots):
    """Presence en mot entier (evite que « super » reagisse a « superieur »)."""
    for mot in mots:
        if re.search(rf"\b{re.escape(mot)}\b", texte):
            return True
    return False


# --------------------------------------------------------------------------
# Recherche semantique locale (TF-IDF + cosinus, pur Python)
# --------------------------------------------------------------------------

class IndexSemantique:
    """Index TF-IDF minimaliste : quelques milliers de documents s'indexent
    en moins d'une seconde et la recherche est instantanee."""

    def __init__(self):
        self._documents = []
        self._vecteurs = []
        self._idf = {}

    @staticmethod
    def _tokens(texte):
        mots = normaliser(texte).split()
        return [m for m in mots if m not in _MOTS_VIDES and len(m) >= 2]

    def vider(self):
        self._documents.clear()
        self._vecteurs.clear()
        self._idf.clear()

    def ajouter(self, texte):
        jetons = self._tokens(texte)
        if jetons:
            self._documents.append((texte, Counter(jetons)))

    def construire(self):
        nb_docs = max(len(self._documents), 1)
        df = Counter()
        for _, compte in self._documents:
            df.update(compte.keys())
        self._idf = {mot: math.log((nb_docs + 1) / (occ + 1)) + 1.0
                     for mot, occ in df.items()}
        self._vecteurs = [self._ponderer(compte) for _, compte in self._documents]

    def _ponderer(self, compte):
        return {mot: occ * self._idf.get(mot, 1.0) for mot, occ in compte.items()}

    @staticmethod
    def _cosinus(v1, v2):
        if not v1 or not v2:
            return 0.0
        petit, grand = (v1, v2) if len(v1) <= len(v2) else (v2, v1)
        dot = sum(p * grand.get(m, 0.0) for m, p in petit.items())
        n1 = math.sqrt(sum(p * p for p in v1.values()))
        n2 = math.sqrt(sum(p * p for p in v2.values()))
        if not n1 or not n2:
            return 0.0
        return dot / (n1 * n2)

    def rechercher(self, requete, seuil=_SEUIL_CORPUS):
        """Retourne (score, texte) du meilleur document au-dessus du seuil."""
        jetons = self._tokens(requete)
        if not jetons or not self._vecteurs:
            return None
        vecteur_q = self._ponderer(Counter(jetons))
        meilleur_score, meilleur_texte = 0.0, None
        for (texte, _), vecteur in zip(self._documents, self._vecteurs):
            score = self._cosinus(vecteur_q, vecteur)
            if score > meilleur_score:
                meilleur_score, meilleur_texte = score, texte
        if meilleur_texte is not None and meilleur_score >= seuil:
            return meilleur_score, meilleur_texte
        return None


# --------------------------------------------------------------------------
# Manuel integre de l'application
# --------------------------------------------------------------------------

MANUEL = [
    {"titre": "Presentation de l'application",
     "clefs": ["presentation", "a quoi sert", "logiciel", "application",
               "gestion scolaire", "fonctionnalites"],
     "texte": ("Gestion Scolaire est le logiciel complet de l'ecole :\n"
               "- Eleves : inscription, fiches, reinscription\n"
               "- Classes, cycles et annees scolaires\n"
               "- Notes, moyennes et bulletins PDF\n"
               "- Presences journalieres\n"
               "- Caisse, tarifs et paiements\n"
               "- Planning, programmes, personnel\n"
               "- Comptes utilisateurs par role, sauvegardes\n"
               "- Synchronisation multi-postes optionnelle.\n"
               "Posez-moi une question sur n'importe quelle section !")},
    {"titre": "Roles et permissions",
     "clefs": ["role", "roles", "permission", "permissions", "directeur peut",
               "gestionnaire peut", "droits", "acces"],
     "texte": ("3 roles existent :\n"
               "- DIRECTEUR : tout (comptes, parametres, personnel, finances,\n"
               "  pedagogie). Il valide la structure diffusee aux autres postes.\n"
               "- GESTIONNAIRE : dashboard, stats, eleves, classes, notes,\n"
               "  presences, planning, caisse, tarifs, paiements, programmes.\n"
               "  Pas de personnel, parametres ni comptes.\n"
               "- Le compte du DERNIER directeur actif ne peut pas etre\n"
               "  desactive ni supprime (protection integree).\n"
               "La session reste ouverte entre deux lancements ; seule une\n"
               "deconnexion volontaire demande l'identification.")},
    {"titre": "Inscrire un eleve",
     "clefs": ["inscrire", "inscription", "nouvel eleve", "ajouter un eleve",
               "nouveau dossier", "matricule", "reinscrire", "reinscription"],
     "texte": ("Pour inscrire un eleve : page ELEVES -> bouton « Nouvelle "
               "Inscription ». Renseignez identite, naissance, classe, parents/"
               "tuteur. Le matricule est genere automatiquement "
               "(ELEV<annee><numero>). Cochez les documents recus (acte, "
               "photos, bulletin).\n"
               "REINSCRIPTION : bouton dedie sur la ligne d'un eleve deja "
               "present : le dossier EXISTANT passe en statut « Inscrit » et "
               "est marque redoublant (aucun doublon cree). Un paiement peut "
               "etre encaisse dans la foulee.\n"
               "Dites-moi juste « inscris un nouvel eleve » et j'ouvre le "
               "formulaire !")},
    {"titre": "Classes et cycles",
     "clefs": ["creer classe", "nouvelle classe", "classe", "capacite",
               "titulaire", "salle", "cycle", "cycles"],
     "texte": ("Page CLASSES : creation (nom, niveau, capacite, salle, "
               "titulaire, cycle), modification, suppression. Supprimer une "
               "classe efface aussi ses eleves, notes, presences, paiements, "
               "planning, tarifs et programmes (confirmation detaillee "
               "affichee).\n"
               "Page CYCLES : Prescolaire / Primaire / College / Lycee par "
               "defaut, plus la gestion des ANNEES SCOLAIRES.\n"
               "Je peux creer directement : « creer une classe 6eme B ».")},
    {"titre": "Annee scolaire active",
     "clefs": ["annee scolaire", "annee active", "changer d annee",
               "basculer annee", "coherence temporelle"],
     "texte": ("Une seule annee scolaire est ACTIVE a la fois (page CYCLES). "
               "Elle structure tout : caisse, inscriptions, presences.\n"
               "Garde de coherence : impossible d'enregistrer des donnees "
               "datees hors de l'annee active.\n"
               "Les annees scolaires ne peuvent pas se chevaucher.")},
    {"titre": "Notes et moyennes",
     "clefs": ["note", "notes", "moyenne", "moyennes", "evaluation",
               "bulletin", "composition", "devoir", "coefficient"],
     "texte": ("Page NOTES, onglet « Saisie » : choisissez classe + matiere + "
               "trimestre, chargez, saisissez Devoir1/Devoir2/Composition "
               "(sur 20) puis ENREGISTREZ avant de changer de selection.\n"
               "Formule : moyenne matiere = (D1 + D2 + 2 x Composition) / 4.\n"
               "Onglet « Moyennes Generales » : moyenne ponderee par les "
                "coefficients + appreciations (configurables dans PARAMETRES).\n"
               "Demandez-moi : « moyenne de <eleve> » ou « moyenne de la "
               "classe <nom> » et je calcule !")},
    {"titre": "Bulletins et exports PDF",
     "clefs": ["pdf", "imprimer", "impression", "export", "certificat",
               "recu", "fiche de paie", "bulletin pdf"],
     "texte": ("Exports PDF disponibles : bulletins (depuis NOTES), recus de "
               "paiement (PAIEMENTS/CAISSE), certificats de frequentation "
               "(ELEVES), fiches de paie (PERSONNEL), releves caisse, "
               "plannings.\nChaque export reprend les parametres de l'ecole "
               "(logo, signatures, ville) definis dans PARAMETRES.")},
    {"titre": "Presences",
     "clefs": ["presence", "presences", "absent", "absence", "absents",
               "retard", "retards", "appel"],
     "texte": ("Page PRESENCES : choisissez classe + date puis « Charger ». "
               "Marquez Present/Absent/Retard eleve par eleve ou utilisez "
               "« Tout present »/« Tout absent », puis enregistrez.\n"
               "La feuille se recharge automatiquement si la date change : "
               "impossible d'enregistrer sous la mauvaise date.\n"
               "Demandez-moi : « qui est absent aujourd'hui ? »")},
    {"titre": "Planning",
     "clefs": ["planning", "emploi du temps", "creneau", "horaire"],
     "texte": ("Page PLANNING : grille par classe et creneau. Bouton "
               "« Modifier la grille » pour passer en mode edition (double-clic "
               "sur une case pour placer matiere + enseignant). Changer de "
               "classe sort automatiquement du mode edition. Export PDF "
               "disponible.")},
    {"titre": "Caisse",
     "clefs": ["caisse", "transaction", "transactions", "entree", "sortie",
               "recette", "depense", "tresorerie"],
     "texte": ("Page CAISSE : enregistrez les ENTREES (recettes) et SORTIES "
               "(depenses), filtrez par type/motif/dates et par ANNEE scolaire "
               "(Active/Toutes), exportez en CSV respectant exactement les "
               "filtres affiches.\nLe solde = entrees - sorties.\n"
               "Dites : « enregistrer une entree de 5000 pour fournitures » "
               "et je m'en occupe !")},
    {"titre": "Tarifs",
     "clefs": ["tarif", "tarifs", "frais", "frais scolaires",
               "montant de scolarite"],
     "texte": ("Page TARIFS : definissez par classe chaque type de frais "
               "(scolarite, inscription, tenue...) et son montant pour "
               "l'annee. Supprimer un tarif modifie les soldes des eleves "
               "concernes (annonce avant confirmation).\nDemandez : « tarifs "
               "de la classe 6eme ».")},
    {"titre": "Paiements",
     "clefs": ["paiement", "paiements", "encaisser", "encaissement",
               "reste a payer", "sur-paiement"],
     "texte": ("Page PAIEMENTS : encaissez par eleve (type de frais, mode, "
               "trimestre). Alerte automatique si le montant depasse le solde "
               "restant (confirmation explicite exigee). Recu PDF genere.\n"
               "Demandez : « combien a paye <eleve> » ou « reste a payer de "
               "<eleve> ».")},
    {"titre": "Programmes",
     "clefs": ["programme", "programmes", "matiere", "matieres",
               "enseignant attribue"],
     "texte": ("Page PROGRAMMES : associez matieres et enseignants a chaque "
               "classe avec leur coefficient (base des moyennes ponderees). "
               "La liste des enseignants est filtree sur le personnel de "
               "fonction Enseignant/Professeur/Instituteur.\n"
               "Je peux creer une matiere : « creer une matiere Histoire "
               "coefficient 2 ».")},
    {"titre": "Personnel",
     "clefs": ["personnel", "enseignant", "enseignants", "salaire", "salaires",
               "masse salariale", "employe", "employes"],
     "texte": ("Page PERSONNEL : gestion des enseignants et du personnel "
               "administratif (coordonnees, salaire > 0 obligatoire, statut "
               "Actif/Inactif), masse salariale affichee, fiche de paie PDF."
               "\nReserve au role DIRECTEUR.\nDemandez : « combien "
               "d'enseignants » ou « masse salariale ».")},
    {"titre": "Parametres et sauvegarde",
     "clefs": ["parametre", "parametres", "logo", "signature", "sauvegarde",
               "sauvegarder", "backup", "restaurer", "restauration",
               "ville ecole"],
     "texte": ("Page PARAMETRES : nom de l'ecole, logo, signataires, ville/"
               "pays, frais par defaut.\nSAUVEGARDE : creez un fichier de "
               "backup a tout moment (liste visible et rechargeable) ; "
               "RESTAURATION en un clic. Conseil : sauvegarde quotidienne sur "
               "cle USB ou disque externe.")},
    {"titre": "Comptes utilisateurs",
     "clefs": ["compte", "comptes", "mot de passe", "utilisateur",
               "utilisateurs", "desactiver un compte", "dernier directeur"],
     "texte": ("Page COMPTES (directeur) : creez les comptes du personnel "
               "avec leur role, reinitialisez les mots de passe (code "
               "aleatoire affiche), desactivez sans supprimer.\nProtections : "
               "impossible de desactiver/supprimer son propre compte ni le "
               "dernier directeur actif.\nChaque utilisateur peut changer son "
               "mot de passe depuis son interface.")},
    {"titre": "Tableaux de bord et statistiques",
     "clefs": ["dashboard", "tableau de bord", "statistique", "statistiques",
               "kpi", "graphique", "graphiques"],
     "texte": ("TABLEAU DE BORD : KPI adaptes a votre role + actions rapides "
               "(nouvelle inscription, nouvelle transaction...) et graphiques "
               "(finances, effectifs) pour le directeur.\nSTATISTIQUES : "
               "graphiques detailles (effectifs par classe/sexe, finances, "
               "presences). Tout se rafraichit automatiquement apres chaque "
               "modification.")},
    {"titre": "Synchronisation multi-postes",
     "clefs": ["synchro", "synchroniser", "synchronisation", "serveur",
               "multi-postes", "multipostes", "autre pc", "autres postes",
               "reseau", "donnees centraux"],
     "texte": ("MODE MULTI-POSTES : un PC fait tourner le serveur (assistant "
               "dedie accessible via le badge en bas de la colonne de "
               "gauche), les autres s'y connectent.\n"
               "- La structure modifiee par le directeur (cycles, classes, "
               "matieres, annees, tarifs) se propage automatiquement aux "
               "autres postes (pull toutes les ~60 s).\n"
               "- Les ecritures locales sont poussees via une file d'attente "
               "anti-doublons des que le serveur revient.\n"
               "- L'app reste 100 % fonctionnelle hors-ligne (Mode Autonome).\n"
               "Dites « etat du serveur », « synchronise maintenant » ou "
               "« combien d'eleves sur le serveur ? »")},
        {"titre": "A propos de l'assistante Charo",
       "clefs": ["charo", "assistant", "ia", "qui es tu", "tu sais faire quoi",
                 "aide", "help", "commandes", "capacites", "llm", "modele"],
       "texte": ("Je suis CHARO, votre assistante scolaire locale et autonome.\n"
                 "Exemples :\n"
                 "- « combien d'eleves en 6eme ? »\n"
                 "- « moyenne de Mambou Junior »\n"
                 "- « solde de la caisse »\n"
                 "- « qui est absent aujourd'hui ? »\n"
                 "- « creer une matiere Histoire coefficient 2 »\n"
                 "- « enregistrer une sortie de 3000 pour carburant »\n"
                 "- « ouvre les paiements »\n"
                 "- « etat du serveur » / « synchronise maintenant »\n"
                 "- Apprenez-moi : « retiens que la reunion est le samedi » ; "
                 "« quand je dis code reponds 1234 » ; « montre ta memoire » ; "
                 "« oublie ... »\n"
                 "- « comment sauvegarder ? » (manuel complet)\n"
                 "- « explique-moi » : je detaillerai mon raisonnement.\n"
                 "- Questions composees : « combien d'eleves et quelle annee «,\n"
                 "  je reponds aux deux en un seul message.\n"
                 "- Suggestions proactives : apres chaque reponse, je vous "
                 "propose des questions liees.\n"
                 "- Mode etendu (ollama) : quand le serveur ollama local est "
                 "lance avec un modele (ex: phi3, gemma), Charo peut repondre "
                 "a des questions generales et conversationnelles au-dela des "
                 "donnees scolaires. Sans ollama, Charo fonctionne en mode "
                 "autonome 100 % offline.\n")},
]

_PAGES_NAV = [
    ("tableau de bord", "dashboard"),
    ("dashboard", "dashboard"),
    ("accueil", "dashboard"),
    ("statistique", "stats"),
    ("eleve", "eleves"),
    ("classe", "classes"),
    ("cycle", "cycles"),
    ("annee scolaire", "cycles"),
    ("note", "notes"),
    ("bulletin", "notes"),
    ("presence", "presences"),
    ("planning", "planning"),
    ("emploi du temps", "planning"),
    ("caisse", "caisse"),
    ("transaction", "caisse"),
    ("tarif", "tarifs"),
    ("frais", "tarifs"),
    ("paiement", "paiements"),
    ("personnel", "personnel"),
    ("programme", "programmes"),
    ("matiere", "programmes"),
    ("parametre", "parametres"),
    ("compte", "comptes"),
]

_PAGES_TITRES = {
    "dashboard": "Tableau de bord", "stats": "Statistiques", "eleves": "Eleves",
    "classes": "Classes", "cycles": "Cycles & Annees", "notes": "Notes",
    "presences": "Presences", "planning": "Planning", "caisse": "Caisse",
    "tarifs": "Tarifs", "paiements": "Paiements", "personnel": "Personnel",
    "programmes": "Programmes", "parametres": "Parametres",
    "comptes": "Comptes",
}

_GENRE_NOM = {"cycle": "un cycle", "matiere": "une matiere",
              "classe": "une classe"}

_CYCLES_DEFAUT = ("prescolaire", "primaire", "college", "lycee")

_REGLE_CLASSE_CYCLE = [
    (r"^p[1-3]\b", "Prescolaire"),
    (r"^(cp|ce|cm)", "Primaire"),
    (r"^(terminale|tale|1ere|2nde|premiere|seconde)", "Lycee"),
    (r"^\d+\s*(eme|ere)\b", "College"),
]


class AssistantIA:
    """Moteur principal. Une instance par utilisateur connecte."""

    TTL_CORPUS = 60.0

    def __init__(self, user):
        self.user = dict(user) if user else None
        from services.auth import RoleAuthorizer
        self.autorisation = RoleAuthorizer(user["role"]) if user else None
        self._attente = None
        self._index_memoire = IndexSemantique()
        self._index_donnees = IndexSemantique()
        self._corpus_date = 0.0
        self._memoire_chargee = False
        self._dernier_eleve_id = None
        self._derniere_classe_id = None
        self.contexte = ContexteConversation()
        self._graphe = GrapheEcole.instance()
        self._vocab_cache = set(_VOCABULAIRE_DE_BASE)
        self._vocab_date = 0.0
        # Suivi de raisonnement pour les explications
        self._derniere_explication = None
        self._derniere_reponse = None
        # Backend LLM optionnel (enhancement, not required)
        self._llm = get_backend()
        self._contexte_conversation = []
        self._historique = []            # (role, texte) pour le LLM, dans l'ordre reel
        # Faits de l'ecole (cache 30 s) injectes dans les prompts LLM.
        self._faits_cache = ""
        self._faits_date = 0.0
        # Apprentissage autonome : journal, feedback, auto-amelioration.
        self._apprentissage = MoteurApprentissage()
        self._derniere_question_brute = None
        self._last_llm_reponse = None
        self._llm_question_originale = None
        self._compteur_tours = 0

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def traiter(self, texte_brut):
        """Point d'entree unique. Retourne :
        {"texte": str, "action": dict|None, "choix": [str,...]|None}"""
        brut = (texte_brut or "").strip()
        # Correction orthographique douce (jamais pendant un flux guide :
        # l'utilisateur y confirme des noms, il ne faut pas les retoucher).
        if brut and self._attente is None and len(brut.split()) >= 2:
            corrige = corriger_phrase(brut, self._vocabulaire())
            if corrige != brut:
                brut = corrige
        t = normaliser(brut)
        if not t:
            return self._aide()
        self._derniere_question_brute = brut
        self._historique.append(("user", brut))
        if len(self._historique) > 10:
            self._historique.pop(0)
        self._compteur_tours += 1
        try:
            if self._compteur_tours % 50 == 0:
                self._apprentissage.ameliorer()
        except Exception:
            pass

        if self._attente is not None:
            return self._avancer_flux(t, brut)

        if _non(t):
            return self._rep("Rien a annuler. Comment puis-je aider ?")

        # Fil de discussion : « et en cm2 ? » / « et ses paiements ? »
        reformulee = self.contexte.reformuler(t)
        if reformulee:
            brut = reformulee
            t = normaliser(reformulee)

        # Demande d'explication sur la derniere reponse
        if _contient_un(t, "explique", "expliquer", "comment tu as",
                        "comment as-tu", "comment ca", "raisonn", "pourquoi"):
            rep = self._essayer_explication(t)
            if rep is not None:
                return rep

        # Questions composees : « X et Y ? » → on traite chaque partie
        if " et " in t and len(t.split()) >= 6:
            rep = self._gerer_question_composee(t, brut)
            if rep is not None:
                return rep

        if len(t.split()) <= 4 and _mot_present(
                t, "bonjour", "salut", "bonsoir", "hello", "coucou", "hey",
                "merci", "super", "genial", "top", "bye", "revoir"):
            if _mot_present(t, "merci"):
                return self._rep("Avec plaisir ! N'hesitez pas si vous avez "
                                 "une autre question.")
            if _mot_present(t, "bye", "revoir"):
                return self._rep(f"A bientot ! {NOM_ASSISTANT} reste "
                                 "disponible ici.")
            return self._rep(
                f"Bonjour {self._prenom_utilisateur()} ! Je suis "
                f"{NOM_ASSISTANT}, votre assistante. Demandez-moi par exemple : "
                "« combien d'eleves ? », « solde de la caisse », « qui est "
                "absent aujourd'hui ? » ou tapez « aide ».",
                choix=self.suggestions())

        resultat_calcul = self._calcul_libre(t)
        if resultat_calcul is not None:
            return resultat_calcul

        # Apprentissage auto des reponses LLM / corrections demandees
        if _contient(t, "cette reponse") and \
                _contient_un(t, "apprendre", "apprends") and \
                self._last_llm_reponse:
            question = getattr(self, "_llm_question_originale", None) or \
                self._derniere_question_brute or "cette reponse"
            self._memo_ajouter("qa", question, self._last_llm_reponse,
                               source="llm")
            self._last_llm_reponse = None
            self._llm_question_originale = None
            return self._rep(
                "C'est retenu et sauvegarde dans ma memoire durable ! La "
                "prochaine fois, je repondrai sans avoir besoin de l'aide "
                "etendue.",
                source="memoire")

        if _contient_un(t, "posez-moi autre chose"):
            return self._rep("Bien sur ! Que voulez-vous savoir ?",
                             choix=self.suggestions())

        if _contient(t, "la bonne reponse") and \
                _contient_un(t, "apprendre", "apprends") and \
                self._derniere_question_brute:
            self._attente = {"type": "apprentissage",
                             "etape": "collecte_reponse",
                             "question": self._derniere_question_brute}
            return self._rep("Bien sur. Quelle est la bonne reponse a "
                             "retenir ? (envoyez-la telle quelle)")

        if _contient_un(t, "statisti", "apprentissage auto", "tes progres",
                        "evolue", "combien de questions"):
            return self._rep(self._forme_stats(), source="moteur")

        if _contient_un(t, "ameliore", "entraine", "fusionne", "dedoublonne"):
            rapport = self.ameliorer(force=True)
            return self._rep(
                "Amelioration terminee :\n"
                f"- {rapport['fusionne']} doublon(s) fusionne(s)\n"
                f"- {rapport['retires']} apprentissage(s) faible(s) retire(s)\n"
                f"- {rapport['memoire']} souvenir(s) actif(s), "
                f"{rapport['journal']} tour(s) journalise(s).",
                source="moteur")

        # Memoire : oublier / consulter / enseigner explicitement
        rep = self._essayer_memoire(t, brut)
        if rep is not None:
            return rep

        # Aide explicite / manuel
        if _contient_un(t, "aide", "help", "manuel", "documentation",
                        "comment ca marche", "que sais tu", "comment faire",
                        "comment puis je", "comment inscrire", "comment creer",
                        "comment enregistrer", "comment imprimer",
                        "comment synchroniser", "comment connecter"):
            sujet = self._chercher_manuel(t)
            if sujet:
                return self._rep(f"[{sujet['titre']}]\n{sujet['texte']}",
                                 source="manuel")
            return self._aide()

        # Synchronisation / multi-postes
        rep = self._essayer_multipostes(t)
        if rep is not None:
            return rep

        # Creations guidees
        rep = self._essayer_creation(t, brut)
        if rep is not None:
            return rep

        # Navigation
        rep = self._essayer_navigation(t)
        if rep is not None:
            return rep

        # Questions metier (ordre de priorite fixe)
        for essai in (
                self._q_graphe, self._q_absences,
                self._q_moyenne_generale, self._q_classement,
                self._q_moyennes, self._q_paiements_eleve,
                self._q_tarifs_classe, self._q_caisse, self._q_personnel,
                self._q_annee_active, self._q_fiche_eleve, self._q_effectifs):
            try:
                rep = essai(t)
            except Exception:
                rep = None
            if rep is not None:
                try:
                    self._noter_contexte(t)
                except Exception:
                    pass
                return rep

        # Memoire apprise (questions enseignees precedemment)
        trouve = self._chercher_memoire(t)
        if trouve is not None:
            return trouve

        # Secours flou : eleve ou classe mal orthographie
        rep = self._secours_flou(t)
        if rep is not None:
            return rep

        # Lecture directe des donnees (index semantique sur la base)
        trouve = self._chercher_dans_donnees(t)
        if trouve is not None:
            return trouve

        # Rien trouve : tenter le LLM, sinon proposer l'apprentissage
        rep = self._essayer_llm_brut(brut)
        if rep is not None:
            return rep
        return self._proposer_apprentissage(brut)

    def _faits_ecole(self):
        """Bilan compact et chiffre de l'ecole (cache 30 s) pour le LLM.

        Le LLM ne doit JAMAIS inventer un chiffre : ce texte lui donne les
        donnees reelles de la base pour construire ses reponses."""
        if self._faits_date and time.monotonic() - self._faits_date < 30.0:
            return self._faits_cache
        parties = []
        try:
            eleves = repos.eleve.eleves()
            filles = sum(1 for e in eleves if e.get("sexe") == "F")
            inscrits = sum(1 for e in eleves
                           if (e.get("statut") or "") == "Inscrit")
            parties.append(f"Ecole : {len(eleves)} eleve(s) enregistre(s) "
                           f"({filles} fille(s), {len(eleves) - filles} "
                           f"garcon(s)), {inscrits} inscrit(s).")
            by_classe = {}
            for e in eleves:
                cl = e.get("classe_nom") or "sans classe"
                by_classe[cl] = by_classe.get(cl, 0) + 1
            if by_classe:
                parties.append("Effectifs par classe : " + ", ".join(
                    f"{k} ({v})" for k, v in sorted(by_classe.items())))
            try:
                entree, sortie, solde = repos.finance.caisse_totals()
                parties.append(f"Caisse : entrees {entree:.0f} FCFA, sorties "
                               f"{sortie:.0f} FCFA, solde {solde:.0f} FCFA.")
            except Exception:
                pass
            try:
                pers = repos.personnel_repo.personnel()
                masse = repos.personnel_repo.masse_salariale()
                parties.append(f"Personnel : {len(pers)} membre(s), masse "
                               f"salariale mensuelle {masse:.0f} FCFA.")
            except Exception:
                pass
            try:
                active = repos.classe.annee_scolaire_active()
                if active:
                    parties.append(f"Annee scolaire active : "
                                   f"{active['libelle']}.")
            except Exception:
                pass
            try:
                mois = datetime.date.today().strftime("%m")
                annee = datetime.date.today().year
                ligne = db.query_one(
                    "SELECT COUNT(*) AS c, COALESCE(SUM(montant), 0) AS s "
                    "FROM paiements WHERE substr(date_paiement, 1, 7) = ?",
                    (f"{annee}-{mois}",))
                if ligne and ligne["c"]:
                    parties.append(f"Paiements du mois en cours : "
                                   f"{ligne['c']} versement(s) pour "
                                   f"{ligne['s']:.0f} FCFA.")
            except Exception:
                pass
        except Exception:
            pass
        self._faits_cache = "\n".join(parties)
        self._faits_date = time.monotonic()
        return self._faits_cache

    def _essayer_llm_brut(self, brut):
        """Fallback LLM : quand le système rule-based ne sait pas répondre,
        essayer de répondre avec le LLM local (si disponible).

        Le LLM est l'ultime recours, jamais le premier : appel court
        (duree_max), reponse bâtie uniquement sur les donnees de l'ecole
        fournies en contexte. Aucune hallucination possible sur les chiffres,
        aucun blocage de l'application."""
        if not self._llm.disponible():
            return None
        if not brut or len(brut) < 6:
            return None
        if self._attente is not None:
            return None

        prompt_systeme = (
            "Tu es Charo, une assistante administrative scolaire très "
            "utile. Tu réponds strictement à partir des DONNEES DE L'ECOLE "
            "fournies ci-dessous. Si l'information demandée n'est pas dans "
            "ces données, dis-le poliment et propose une question proche "
            "gérable. Ne JAMAIS inventer de chiffre, de classe, d'élève ou "
            "de tarif. Réponds en français, concis, avec les montants en "
            "FCFA."
        )
        messages = [
            {"role": "system", "content": prompt_systeme
             + "\n\nDONNEES ACTUELLES :\n" +
             (self._faits_ecole() or "(aucune donnee dans la base)")},
        ]
        for role, contenu in self._historique[-6:]:
            messages.append({"role": role, "content": contenu})
        messages.append({"role": "user", "content": brut})
        try:
            reponse = self._llm._generer(messages)
        except Exception:
            return None
        if reponse:
            self._last_llm_reponse = reponse
            self._llm_question_originale = self._derniere_question_brute or brut
            return self._rep(
                f"[Assistance etendue]\n{reponse}",
                choix=["Apprendre cette reponse", "Posez-moi autre chose"],
                source="llm")
        return None

    def suggestions(self):
        """Suggestions contextuelles, améliorées par le LLM quand disponible.

        Le LLM ne reformule les suggestions que si le modèle est déjà chargé
        en mémoire (sinon, le premier appel prend ~30s ce qui bloquerait
        l'interface)."""
        base = ["Combien d'eleves ?", "Solde de la caisse",
                "Qui est absent aujourd'hui ?", "Aide"]
        if not self._llm.disponible() or not self._llm._modele_charge:
            return base
        try:
            ctx = "; ".join(self._contexte_conversation[-3:]) if self._contexte_conversation else ""
            sug = self._llm.ameliorer_suggestions(base, ctx)
            return sug if sug else base
        except Exception:
            return base

    def _suggestions_proactives(self, contexte_type=None):
        """Suggestions de suivi contextuelles selon le type de question."""
        base = self.suggestions()
        if contexte_type == "eleve":
            return ["Moyenne de " + self._nom_dernier_eleve(),
                    "Paiements de " + self._nom_dernier_eleve(),
                    "Fiche de " + self._nom_dernier_eleve()]
        if contexte_type == "classe":
            return ["Moyenne de la classe " + self._nom_derniere_classe(),
                    "Tarifs de la classe " + self._nom_derniere_classe(),
                    "Combien de filles en " + self._nom_derniere_classe()]
        if contexte_type == "caisse":
            return ["Dernières transactions", "Masse salariale",
                    "Combien d'eleves ?"]
        if contexte_type == "absences":
            return ["Qui est absent hier ?", "Solde de la caisse",
                    "Moyenne de la classe " + self._nom_derniere_classe()]
        return base

    def _nom_dernier_eleve(self):
        if self._dernier_eleve_id:
            e = repos.eleve.eleve_by_id(self._dernier_eleve_id)
            if e:
                return f"{e['prenom']} {e['nom']}".strip()
        return "l'élève"

    def _nom_derniere_classe(self):
        if self._derniere_classe_id:
            c = db.query_one("SELECT nom FROM classes WHERE id = ?",
                             (self._derniere_classe_id,))
            if c:
                return c["nom"]
        return "la classe"

    def _essayer_explication(self, t):
        """Reproduit le raisonnement de la derniere reponse.

        Avec le LLM disponible, le raisonnement devient plus riche et
        naturel — comme les IA modernes (ChatGPT, etc.) qui détaillent
        leur chaîne de pensée."""
        if _contient_un(t, "pourquoi") and self._derniere_explication:
            if self._llm.disponible() and self._derniere_reponse:
                question = self._contexte_conversation[-1] \
                    if self._contexte_conversation else ""
                faits = f"{self._derniere_reponse.get('texte', '')}\n\n" \
                        f"{self._faits_ecole()}"
                raisonnement = self._llm.raisonner(question, faits,
                                                   duree_max=6.0)
                if raisonnement:
                    texte = f"{self._derniere_explication}\n\n{raisonnement}"
                    self._derniere_explication = None
                    return self._rep(texte)
            return self._rep(self._derniere_explication)
        if not self._derniere_explication:
            return None
        exp = self._derniere_explication
        self._derniere_explication = None
        return self._rep(exp)

    def _gerer_question_composee(self, t, brut):
        """Découpe une question du type « X et Y ? » en deux requêtes
        indépendantes, exécute la première, puis mémorise la seconde pour
        un traitement en chaîne (l'utilisateur peut relancer ou Charo répond
        aux deux en une seule)."""
        parties = re.split(r"\s+ et\s+", t)
        if len(parties) < 2:
            return None
        if len(parties[0].split()) < 3 or len(parties[1].split()) < 3:
            return None
        rep1 = self.traiter(parties[0])
        if not rep1:
            return None
        # Traitement de la seconde partie
        rep2 = self.traiter(parties[1])
        if rep2 and rep2.get("texte"):
            texte_combine = f"{rep1['texte']}\n\n{rep2['texte']}"
            return self._rep(texte_combine, choix=rep2.get("choix"))
        return rep1

    def reinitialiser(self):
        """Nouvelle discussion : abandon du flux en cours + oublie le fil."""
        self._attente = None
        self.contexte.vider()

    # ------------------------------------------------------------------
    # Modules avances : vocabulaire, contexte, graphe, calcul
    # ------------------------------------------------------------------

    def _vocabulaire(self):
        """Vocabulaire de correction = mots du domaine + noms reels de la
        base (classes, eleves, matieres, cycles, personnel). Cache 60 s."""
        if time.monotonic() - self._vocab_date < 60.0:
            return self._vocab_cache
        mots = {normaliser_ia(m) for m in _VOCABULAIRE_DE_BASE}
        try:
            for sujet in MANUEL:
                mots.update(normaliser_ia(c) for c in sujet["clefs"])
            conn = db.connect()
            for (nom,) in conn.execute("SELECT nom FROM classes"):
                # On exclut les noms de classes numeriques (« 3eme », « 4eme »)
                # du vocabulaire de correction : ils risquent d'empiéter sur
                # les indications de periode (« 2eme trimestre » → « 3eme »).
                if not re.match(r"^\d+(bis|ter)?\s*(eme|er|re)\b", normaliser_ia(nom)):
                    mots.add(normaliser_ia(nom))
            for (nom,) in conn.execute("SELECT nom FROM matieres"):
                mots.add(normaliser_ia(nom))
            for (nom,) in conn.execute("SELECT nom FROM cycles"):
                mots.add(normaliser_ia(nom))
            for prenom, nom in conn.execute(
                    "SELECT prenom, nom FROM eleves LIMIT 2000"):
                mots.add(normaliser_ia(prenom))
                mots.add(normaliser_ia(nom))
        except Exception:
            pass
        mots.discard("")
        self._vocab_cache = mots
        self._vocab_date = time.monotonic()
        return mots

    def _noter_contexte(self, t):
        """Memorise le tour utile pour les anaphores (« et en cm2 ? »)."""
        eleve_label = None
        if self._dernier_eleve_id:
            info = self._graphe.label_de(f"eleve:{self._dernier_eleve_id}")
            if info:
                eleve_label = info
        self.contexte.noter(t, eleve=eleve_label)

    def _q_graphe(self, t):
        """Theorie des graphes : liens entre entites + vue structure."""
        if not _contient_un(t, "lien", "liens", "relation", "relations",
                            "chemin", "relie", "relier", "structure",
                            "organisation", "organisee", "organise"):
            return None
        graphe = self._graphe
        m = re.search(
            r"(?:lien|relation|chemin|relie|relier)\w*\s+(?:entre\s+)?"
            r"(.+?)\s+et\s+(.+?)\s*\??$", t)
        if m and len(m.group(1)) > 1 and len(m.group(2)) > 1:
            pa = graphe.trouver(m.group(1))
            pb = graphe.trouver(m.group(2))
            if not pa or not pb:
                manquant = m.group(1) if not pa else m.group(2)
                return self._rep(
                    f"Je ne trouve pas « {manquant} » dans les donnees "
                    "de l'ecole. Verifiez l'orthographe.")
            ids = graphe.chemin_plus_court(pa[0], pb[0])
            if ids is None:
                return self._rep(
                    f"Aucun lien entre « {pa[1]['label']} » et "
                    f"« {pb[1]['label']} » dans les donnees actuelles.")
            labels, relations = graphe.relations_du_chemin(ids)
            fleches = " ".join(
                f"—{rel}→ {lab}" for rel, lab in zip(relations, labels[1:]))
            return self._rep(
                f"Lien le plus court : {labels[0]} {fleches} "
                f"({len(ids) - 1} relation(s)).",
                choix=["Structure de l'ecole"])
        if _contient_un(t, "structure", "organisation", "organisee",
                        "organise"):
            st = graphe.stats()
            lignes = ", ".join(
                f"{v} {k}s" for k, v in sorted(st["comptages"].items()))
            hubs = "; ".join(
                f"{nom} ({deg} liens)" for nom, deg in st["hubs"]) or "aucun"
            return self._rep(
                f"Voici la structure de l'ecole : {lignes}, soit "
                f"{st['total_noeuds']} elements et {st['total_relations']} "
                f"relations.\nElements les plus connectes : {hubs}.")
        return None

    # ------------------------------------------------------------------
    # Calcul libre (calculatrice sure basee AST — voir services/ia/maths.py)
    # ------------------------------------------------------------------
    # Helpers internes
    # ------------------------------------------------------------------

    def _rep(self, texte, action=None, choix=None, explication=None,
             suggestions=None, llme=False, source="moteur"):
        """Crée une réponse structurée.

        Chaque réponse livrée est journalisée (moteur d'apprentissage
        autonome) avec sa source (memoire/llm/corpus/manuel/...).
        Si *llme* est True et le backend LLM est disponible, le texte est
        reformulé pour être plus naturel et conversationnel (comme les IA
        modernes). Le texte original est conservé en secours."""
        texte_final = texte.strip()
        if llme and self._llm.disponible() and texte_final:
            reformule = self._llm.reformuler_naturel(
                texte_final,
                self._contexte_conversation[-1] if self._contexte_conversation else "")
            if reformule:
                texte_final = reformule
        rep = {"texte": texte_final, "action": action, "choix": choix}
        self._derniere_reponse = rep
        if explication:
            self._derniere_explication = explication
        if suggestions:
            rep["suggestions"] = suggestions
        self._contexte_conversation.append(texte.strip())
        if len(self._contexte_conversation) > 10:
            self._contexte_conversation.pop(0)
        self._historique.append(("assistant", texte.strip()))
        if len(self._historique) > 10:
            self._historique.pop(0)
        try:
            self._apprentissage.consigner(self._derniere_question_brute,
                                          texte_final, source)
        except Exception:
            pass
        return rep

    def _prenom_utilisateur(self):
        if not self.user:
            return ""
        prenom = (self.user.get("prenom") or "")
        if not prenom:
            nom_complet = self.user.get("nom_complet") or ""
            prenom = nom_complet.split()[0] if nom_complet else ""
        return prenom or (self.user.get("username") or "")

    def _verifier_acces(self, page, edition=False):
        """None si OK, sinon une reponse de refus prete."""
        if self.autorisation is None:
            return None
        ok_edition = self.autorisation.can_edit(page)
        ok_vue = self.autorisation.allowed(page)
        if edition and not ok_edition:
            titre = _PAGES_TITRES.get(page, page)
            return self._rep(
                "Votre profil ne permet pas de faire cette operation dans "
                f"{titre} (consultation seule ou section reservee). "
                "Demandez au directeur.")
        if not edition and not ok_vue:
            titre = _PAGES_TITRES.get(page, page)
            return self._rep(
                f"Votre profil ({ROLE_LABELS.get(self.user['role'], self.user['role'])}) "
                f"ne permet pas d'acceder a la section {titre}. "
                "Adressez-vous au directeur.")
        return None

    # ------------------------------------------------------------------
    # Calcul libre (arithmetique sure)
    # ------------------------------------------------------------------

    def _calcul_libre(self, t):
        resultat = ia_maths.calculer(t)
        if resultat is None:
            return None
        if resultat.get("division_par_zero"):
            return self._rep("Division par zero impossible.")
        if resultat.get("erreur"):
            return self._rep(f"Calcul impossible : {resultat['erreur']}")
        valeur = resultat["valeur"]
        affichage = (resultat["expression"].replace("**", "^")
                     .replace("*", " x ").replace("/", " / "))
        texte = f"{affichage} = {valeur}"
        if isinstance(valeur, int) and abs(valeur) >= 1000:
            texte += f"  ({formater_fcfa(valeur)})"
        explication = (f"J'ai reconnu une expression arithmetique dans votre "
                       f"question. J'ai evalué : {affichage}, "
                       f"ce qui donne {valeur}.")
        return self._rep(texte, explication=explication,
                         suggestions=["125000 - 45000", "Combien d'eleves ?"])

    # ------------------------------------------------------------------
    # Manuel
    # ------------------------------------------------------------------

    def _chercher_manuel(self, t):
        meilleure, score_max = None, 0
        commence_par_comment = t.startswith("comment") or "comment" in t
        for sujet in MANUEL:
            score = sum(1 for cle in sujet["clefs"] if cle in t)
            if commence_par_comment:
                score += 1
            if score > score_max:
                meilleure, score_max = sujet, score
        return meilleure if score_max >= 2 else None

    # ------------------------------------------------------------------
    # Memoire apprise (lecture + apprentissage persistant)
    # ------------------------------------------------------------------

    def _assurer_table_memoire(self):
        self._apprentissage.ensure_tables()

    def _charger_index_memoire(self):
        if self._memoire_chargee:
            return
        self._assurer_table_memoire()
        self._index_memoire.vider()
        for ligne in db.query("SELECT * FROM ia_memoire ORDER BY id"):
            texte_clef = ligne["question"] if ligne["type"] == "qa" \
                else f"{ligne['question']} {ligne['reponse']}"
            self._index_memoire.ajouter(texte_clef)
        self._index_memoire.construire()
        self._memoire_chargee = True

    def _memo_ajouter(self, type_mem, question, reponse_txt, source="manuel"):
        self._assurer_table_memoire()
        db.execute(
            "INSERT INTO ia_memoire (type, question, reponse, source)"
            " VALUES (?, ?, ?, ?)",
            (type_mem, question[:200], reponse_txt[:2000], source))
        self._memoire_chargee = False
        self._charger_index_memoire()

    def _chercher_memoire(self, t):
        self._charger_index_memoire()
        resultat = self._index_memoire.rechercher(t, seuil=_SEUIL_MEMOIRE)
        if resultat is None:
            return None
        score, texte_clef = resultat
        ligne = None
        for candidate in db.query(
                "SELECT * FROM ia_memoire ORDER BY LENGTH(question) DESC"):
            clef = candidate["question"] if candidate["type"] == "qa" \
                else f"{candidate['question']} {candidate['reponse']}"
            if normaliser(clef) == normaliser(texte_clef):
                ligne = candidate
                break
        if ligne is None:
            return None
        try:
            self._apprentissage.vu_memoire(ligne["id"])
        except Exception:
            pass
        etiquette = "appris" if ligne["type"] == "qa" else "fait retenu"
        return self._rep(f"{ligne['reponse']}\n({etiquette} le "
                         f"{ligne['appris_le'][:10]}, pertinence "
                         f"{int(score * 100)}%)", source="memoire")

    def _essayer_memoire(self, t, brut):
        if _contient_un(t, "oublie", "oublier", "efface la memoire",
                        "vide la memoire"):
            if "tout" in t:
                self._attente = {"type": "oublie_tout", "etape": "confirmation"}
                return self._rep(
                    "Voulez-vous vraiment effacer TOUT ce que j'ai appris ? "
                    "Cette action est definitive.", choix=["Oui", "Non"])
            motif = self._extraire_apres(brut.lower(), ("oublie ", "oublier "))
            if not motif:
                return self._rep("Que dois-je oublier ? (ex : « oublie le "
                                 "code » ou « oublie tout »)")
            self._assurer_table_memoire()
            lignes = db.query(
                "SELECT id, question FROM ia_memoire WHERE question LIKE ? "
                "OR reponse LIKE ?", (f"%{motif}%", f"%{motif}%"))
            for l in lignes:
                db.execute("DELETE FROM ia_memoire WHERE id = ?", (l["id"],))
            self._memoire_chargee = False
            if lignes:
                return self._rep(f"Oublie ! {len(lignes)} element(s) supprime(s) "
                                 f"de ma memoire.")
            return self._rep(f"Rien sur « {motif} » dans ma memoire.")

        if _contient_un(t, "ta memoire", "ce que tu as appris", "ce que tu sais",
                        "liste appris", "memorise"):
            self._assurer_table_memoire()
            lignes = db.query("SELECT * FROM ia_memoire ORDER BY id DESC LIMIT 20")
            if not lignes:
                return self._rep("Ma memoire est vide pour l'instant. "
                                 "Enseignez-moi : « retiens que ... » ou "
                                 "« quand je dis X reponds Y ».")
            parties = [f"Memoire de {NOM_ASSISTANT} ({len(lignes)} element(s)) :"]
            for l in lignes:
                if l["type"] == "qa":
                    parties.append(f"- Si « {l['question']} » -> {l['reponse']}")
                else:
                    parties.append(f"- Fait : {l['reponse']}")
            return self._rep("\n".join(parties))

        m = re.search(r"(?:retiens|retenir|memorise|rappelle toi) que (.+)", brut,
                      re.IGNORECASE)
        if m:
            fait = m.group(1).strip()
            self._memo_ajouter("fait", fait, fait)
            return self._rep(f"Retenu ! Je me souviendrai que : {fait}")

        m = re.search(r"(?:quand je dis|si je dis|quand j ecris)\s+(.+?)"
                      r"\s*(?:reponds?|repond moi|dis|tu dis)\s+(.+)", brut,
                      re.IGNORECASE)
        if m:
            question, reponse_txt = m.group(1).strip("? ."), m.group(2).strip()
            self._memo_ajouter("qa", question, reponse_txt)
            return self._rep(f"Appris ! Des que vous parlerez de « {question} », "
                             f"je repondrai : {reponse_txt}")

        if _contient_un(t, "apprends", "apprendre") and \
                not _contient_un(t, "apprentissage auto"):
            return self._rep(
                "Pour m'apprendre quelque chose :\n"
                "- « retiens que <information> »\n"
                "- « quand je dis <mot> reponds <ma reponse> »\n"
                "- ou posez-moi une question : si je ne sais pas, je vous "
                "proposerai de m'apprendre la reponse.")

        return None

    def _proposer_apprentissage(self, brut_original):
        if not brut_original or len(brut_original) < 4:
            return self._aide()
        self._attente = {"type": "apprentissage", "etape": "proposition",
                         "question": brut_original}
        return self._rep(
            f"Je n'ai pas de reponse pour : « {brut_original} ».\n"
            "Voulez-vous me l'apprendre ? (oui / non)",
            choix=["Oui", "Non"])

    # ------------------------------------------------------------------
    # Machine a etats generale (creations + apprentissage + confirmations)
    # ------------------------------------------------------------------

    def _avancer_flux(self, t, brut):
        flux = self._attente
        genre = flux["type"]

        if genre == "apprentissage":
            return self._flux_apprentissage(t, brut, flux)

        if genre == "oublie_tout":
            self.reinitialiser()
            if _oui(t):
                self._assurer_table_memoire()
                db.execute("DELETE FROM ia_memoire")
                self._memoire_chargee = False
                return self._rep("Memoire entierement effacee.")
            return self._rep("Effacement annule. Ma memoire est intacte.")

        if _non(t):
            self.reinitialiser()
            return self._rep("Operation annulee. Rien n'a ete cree.")

        if genre == "transaction":
            return self._flux_transaction(t, brut, flux)

        donnees = flux["donnees"]
        if flux["etape"] == "collecte":
            champ = "nom"
            if donnees.get(champ) in (None, ""):
                if len(t.split()) > 6 or "?" in t:
                    return self._rep(f"Quel nom pour {_GENRE_NOM[genre]} ?")
                donnees[champ] = brut.strip()[:40]
            if genre == "matiere" and donnees.get("coefficient") is None:
                flux["etape"] = "coeff"
                return self._rep("Quel coefficient pour cette matiere ? "
                                 "(un nombre, ou 1 par defaut)", choix=["1"])
            if genre == "classe" and donnees.get("cycle") is None:
                cycle_devine = self._deviner_cycle(donnees["nom"])
                if not cycle_devine:
                    for cyc in _CYCLES_DEFAUT:
                        if cyc in t:
                            cycle_devine = cyc.capitalize()
                            break
                donnees["cycle"] = cycle_devine
            flux["etape"] = "confirmation"
            return self._resume_confirmation(flux)

        if flux["etape"] == "coeff":
            m = re.search(r"(\d+(?:[.,]\d+)?)", t)
            donnees["coefficient"] = float(m.group(1).replace(",", ".")) if m else 1.0
            flux["etape"] = "confirmation"
            return self._resume_confirmation(flux)

        if flux["etape"] != "confirmation":
            self.reinitialiser()
            return self._rep("Etat interne inattendu, operation annulee.")

        if not _oui(t):
            return self._rep("Repondez « oui » pour confirmer ou « non » "
                             "pour annuler.", choix=["Oui", "Non"])

        try:
            if genre == "cycle":
                repos.classe.add_cycle(donnees["nom"])
                message = f"Cycle « {donnees['nom']} » cree avec succes."
                page_suite = "cycles"
            elif genre == "matiere":
                coeff = donnees.get("coefficient") or 1
                repos.pedagogie.add_matiere(donnees["nom"], coeff)
                message = (f"Matiere « {donnees['nom']} » creee "
                           f"(coefficient {coeff:g}).")
                page_suite = "programmes"
            elif genre == "classe":
                cycle_id = None
                nom_cycle = donnees.get("cycle")
                if nom_cycle:
                    ligne = db.query_one(
                        "SELECT id FROM cycles WHERE nom = ? COLLATE NOCASE",
                        (nom_cycle,))
                    cycle_id = ligne["id"] if ligne else None
                repos.classe.add_classe(donnees["nom"], donnees["nom"], 50,
                                        "", "", cycle_id)
                message = (f"Classe « {donnees['nom']} » creee (capacite 50, "
                           f"cycle : {nom_cycle or 'non defini'}).")
                page_suite = "classes"
            else:
                self.reinitialiser()
                return self._rep("Type de creation inconnu, annule.")
        except Exception as exc:
            self.reinitialiser()
            return self._rep(
                f"Echec de la creation : {exc}\n"
                "Un doublon existe peut-etre deja (nom identique).")
        self.reinitialiser()
        return self._rep(message, action={"type": "navigate", "page": page_suite})

    def _flux_apprentissage(self, t, brut, flux):
        if flux["etape"] == "proposition":
            self.reinitialiser()
            if _oui(t):
                self._attente = {"type": "apprentissage",
                                 "etape": "collecte_reponse",
                                 "question": flux["question"]}
                return self._rep("D'accord : quelle est la reponse que je "
                                 "dois retenir ? (envoyez-la telle quelle)")
            return self._rep("Pas de probleme. Posez-moi autre chose !")
        # etape collecte_reponse
        question = flux["question"]
        reponse_txt = brut.strip()
        self.reinitialiser()
        if not reponse_txt or _non(t):
            return self._rep("Apprentissage abandonne.")
        self._memo_ajouter("qa", question, reponse_txt)
        return self._rep(f"C'est retenu ! La prochaine fois que vous "
                         f"demandez « {question} », je repondrai : {reponse_txt}")

    def _flux_transaction(self, t, brut, flux):
        donnees = flux["donnees"]
        if flux["etape"] == "confirmation":
            if _oui(t):
                return self._executer_transaction(donnees)
            return self._rep("Repondez « oui » pour confirmer ou « non » "
                             "pour annuler.", choix=["Oui", "Non"])
        if donnees.get("montant") is None:
            montant = self._extraire_montant(t, allow_petit=True)
            if montant is None:
                mot_type = "entree (recette)" if donnees["type_trans"] == "entree" \
                    else "sortie (depense)"
                return self._rep(f"Quel montant pour cette {mot_type} ?")
            donnees["montant"] = montant
            return self._avancer_flux(t, brut)
        if donnees.get("beneficiaire") is None:
            benef = self._extraire_apres(t, ("beneficiaire ", "paye a "))
            if benef is None and flux["etape"] == "collecte_demandee":
                donnees["beneficiaire"] = brut.strip()[:60] or "-"
            elif benef is not None:
                donnees["beneficiaire"] = benef
            if donnees.get("beneficiaire") in (None, ""):
                flux["etape"] = "collecte_demandee"
                return self._rep("Au nom de qui (beneficiaire) ? Vous pouvez "
                                 "aussi repondre « - ».")
        if donnees.get("motif") is None:
            motif = self._extraire_apres(t, ("pour ", "motif "))
            if motif is not None:
                donnees["motif"] = motif
        flux["etape"] = "confirmation"
        return self._resume_confirmation(flux)

    def _executer_transaction(self, donnees):
        self.reinitialiser()
        try:
            reference = repos.finance.add_transaction(
                donnees["type_trans"], donnees["montant"],
                donnees.get("motif") or "-", "Assistant IA",
                donnees.get("beneficiaire") or "-")
        except Exception as exc:
            return self._rep(f"Echec de l'enregistrement en caisse : {exc}")
        type_label = "Entree" if donnees["type_trans"] == "entree" else "Sortie"
        return self._rep(
            f"{type_label} de {formater_fcfa(donnees['montant'])} enregistree "
            f"(reference {reference}).", action={"type": "navigate",
                                                 "page": "caisse"})

    def _deviner_cycle(self, nom):
        if not nom:
            return None
        n = normaliser(nom)
        for motif, cycle in _REGLE_CLASSE_CYCLE:
            if re.match(motif, n):
                return cycle
        return None

    def _resume_confirmation(self, flux):
        genre, d = flux["type"], flux["donnees"]
        if genre == "transaction":
            resume = (f"Nouvelle {'SORTIE (depense)' if d['type_trans'] == 'sortie' else 'ENTREE (recette)'}\n"
                      f"- Montant : {formater_fcfa(d.get('montant') or 0)}\n"
                      f"- Motif : {d.get('motif') or '-'}\n"
                      f"- Beneficiaire : {d.get('beneficiaire') or '-'}\n"
                      "Confirmez-vous l'enregistrement en caisse ?")
        elif genre == "cycle":
            resume = f"Creer le cycle « {d.get('nom')} » ?"
        elif genre == "matiere":
            resume = (f"Creer la matiere « {d.get('nom')} » "
                      f"(coefficient {(d.get('coefficient') or 1):g}) ?")
        else:
            resume = (f"Creer la classe « {d.get('nom')} » "
                      f"(capacite 50, cycle : {d.get('cycle') or 'non defini'}) ?")
        return self._rep(resume, choix=["Oui", "Non"])

    # ------------------------------------------------------------------
    # Multi-postes / serveur
    # ------------------------------------------------------------------

    def _essayer_multipostes(self, t):
        parle_serveur = _contient_un(
            t, "serveur", "synchro", "synchronis", "multiposte", "multi poste",
            "autre pc", "autres pc", "autre poste", "autres postes",
            "reseau local", "donnees central")
        if not parle_serveur:
            return None

        if _contient_un(t, "synchronis", "recupere", "rafraich"):
            if not self._sync_actif():
                return self._rep(
                    "La synchronisation est desactivee sur ce poste (Mode "
                    "Autonome). Ouvrez l'assistant multi-postes via le badge "
                    "en bas de la colonne de gauche pour l'activer.",
                    action={"type": "ping_serveur"})
            return self._rep("Lancement de la recuperation depuis le serveur...",
                             action={"type": "sync_now"})

        if _contient_un(t, "combien", "nombre", "total", "liste") \
                and _contient_un(t, "eleve", "classe", "paiement"):
            quoi = "total_eleves"
            if "paiement" in t:
                quoi = "total_paiements"
            elif "classe" in t:
                quoi = "classes"
            if not self._sync_actif():
                return self._rep(
                    "Ce poste est en Mode Autonome : les donnees des autres "
                    "PC ne sont pas accessibles. Activez la synchronisation "
                    "via le badge en bas a gauche.",
                    action={"type": "ping_serveur"})
            return self._rep("J'interroge le serveur central...",
                             action={"type": "requete_distant", "quoi": quoi})

        en_attente = db.query_one(
            "SELECT COUNT(*) AS c FROM file_attente_synchro WHERE status='PENDING'")
        nb_attente = en_attente["c"] if en_attente else 0
        if self._sync_actif():
            texte = (f"Etat multi-postes : synchronisation ACTIVEE. "
                     f"{nb_attente} ecriture(s) locale(s) en attente d'envoi. "
                     "Je verifie la joignabilite du serveur...")
        else:
            texte = ("Etat multi-postes : Mode AUTONOME (synchronisation "
                     "desactivee). Les donnees restent sur ce poste ; activez "
                     "la connexion via le badge en bas a gauche pour partager "
                     "avec les autres PC.")
        return self._rep(texte, action={"type": "ping_serveur"})

    @staticmethod
    def _sync_actif():
        from core import network
        return network.sync_active()

    # ------------------------------------------------------------------
    # Creations guidees
    # ------------------------------------------------------------------

    def _essayer_creation(self, t, brut):
        if not _contient_un(t, "cree", "creer", "creee", "ajoute", "ajouter",
                            "nouvelle", "nouveau", "enregistre", "enregistrer"):
            return None
        if _contient_un(t, "dernier", "derniere", "recent", "recente",
                        "historique", "liste", "combien", "nombre", "effectif"):
            return None

        if _contient_un(t, "entree", "sortie", "recette", "depense",
                        "transaction"):
            refus = self._verifier_acces("caisse", edition=True)
            if refus:
                return refus
            type_trans = "sortie" if _contient_un(t, "sortie", "depense") \
                else "entree"
            self._attente = {"type": "transaction", "etape": "collecte",
                             "donnees": {"type_trans": type_trans,
                                         "montant": self._extraire_montant(t),
                                         "motif": self._extraire_apres(t, ("pour ", "motif ")),
                                         "beneficiaire": self._extraire_apres(t, ("beneficiaire ", "paye a "))}}
            return self._avancer_flux(normaliser(brut), brut)

        if "cycle" in t:
            refus = self._verifier_acces("cycles", edition=True)
            if refus:
                return refus
            nom = self._extraire_nom_apres(brut, ("cycle",))
            self._attente = {"type": "cycle", "etape": "collecte",
                             "donnees": {"nom": nom}}
            if not nom:
                return self._rep("D'accord. Quel nom pour ce nouveau cycle ?")
            return self._avancer_flux(normaliser(brut), brut)

        if "matiere" in t:
            refus = self._verifier_acces("programmes", edition=True)
            if refus:
                return refus
            coeff = None
            m = re.search(r"coeff(?:icient)?\s*:?\s*(\d+(?:[.,]\d+)?)", t)
            if m:
                coeff = float(m.group(1).replace(",", "."))
            nom = self._extraire_nom_apres(brut, ("matiere",))
            self._attente = {"type": "matiere", "etape": "collecte",
                             "donnees": {"nom": nom, "coefficient": coeff}}
            if not nom:
                return self._rep("D'accord. Quel nom pour cette nouvelle "
                                 "matiere ?")
            return self._avancer_flux(normaliser(brut), brut)

        if "classe" in t:
            refus = self._verifier_acces("classes", edition=True)
            if refus:
                return refus
            nom = self._extraire_nom_apres(brut, ("classe",))
            self._attente = {"type": "classe", "etape": "collecte",
                             "donnees": {"nom": nom}}
            if not nom:
                return self._rep("D'accord. Quel nom pour cette nouvelle "
                                 "classe ? (ex : 6eme B)")
            return self._avancer_flux(normaliser(brut), brut)

        if _contient_un(t, "eleve", "dossier", "inscription"):
            refus = self._verifier_acces("eleves", edition=True)
            if refus:
                return refus
            return self._rep(
                "J'ouvre le formulaire d'inscription complet (identite, "
                "parents, documents, paiement eventuel).",
                action={"type": "dialog", "dialog": "inscription"})

        return None

    @staticmethod
    def _extraire_montant(t, allow_petit=False):
        m = re.search(
            r"(?:de|montant|somme)\s+(\d[\d\s]*(?:[.,]\d{1,2})?)\s*(?:fcfa|franc)?", t)
        if not m:
            motif = r"\b(\d{4,})\b" if not allow_petit else r"\b(\d{2,})\b"
            m = re.search(motif, t)
        if not m:
            return None
        brut_nb = m.group(1).replace(" ", "").replace(",", ".")
        try:
            return round(float(brut_nb), 2)
        except ValueError:
            return None

    @staticmethod
    def _extraire_apres(t, prefixes):
        for pref in prefixes:
            idx = t.find(pref)
            if idx >= 0:
                suite = t[idx + len(pref):].strip()
                suite = re.split(r"\b(beneficiaire|paye a|aujourd|hier|montant)\b",
                                 suite)[0].strip(" ,.-")
                if suite:
                    return suite[:60]
        return None

    @staticmethod
    def _extraire_nom_apres(brut, cibles):
        for cible in cibles:
            m = re.search(rf"{cible}\s+(?:de\s+|:)?(.+)", brut, re.IGNORECASE)
            if m:
                nom = m.group(1)
                nom = re.sub(r"\b(coefficient|coeff|capacite|salle|titulaire)"
                             r"\b.*$", "", nom, flags=re.IGNORECASE).strip()
                nom = nom.strip(" ,.:;-")
                if nom:
                    return nom[:40]
        return None

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _essayer_navigation(self, t):
        if not _contient_un(t, "ouvre", "ouvrir", "affiche", "afficher",
                            "montre moi", "aller", "va a", "va aux", "vais",
                            "amene", "emmene"):
            return None
        for mot_clef, page in _PAGES_NAV:
            if mot_clef in t:
                refus = self._verifier_acces(page)
                if refus:
                    return refus
                return self._rep(f"J'ouvre la section {_PAGES_TITRES[page]} "
                                 "pour vous.",
                                 action={"type": "navigate", "page": page})
        return None

    # ------------------------------------------------------------------
    # Questions : presences
    # ------------------------------------------------------------------

    def _q_absences(self, t):
        if not _contient_un(t, "absent", "absente", "absence", "absences",
                            "retard", "retards", "manquant"):
            return None
        jour = datetime.date.today()
        if "hier" in t:
            jour -= datetime.timedelta(days=1)
        lignes = db.query(
            """SELECT e.nom, e.prenom, c.nom AS classe, p.statut, p.motif
               FROM presences p JOIN eleves e ON e.id = p.eleve_id
               LEFT JOIN classes c ON c.id = e.classe_id
               WHERE p.date = ? AND p.statut != 'Present'
               ORDER BY c.nom, e.nom""", (jour.isoformat(),))
        presents = db.query_one(
            "SELECT COUNT(*) AS c FROM presences WHERE date = ? "
            "AND statut='Present'", (jour.isoformat(),))
        nb_pres = presents["c"] if presents else 0
        date_fr = formater_date(jour.isoformat())
        if not lignes:
            return self._rep(f"Aucune absence ni retard enregistre le {date_fr} "
                             f"({nb_pres} present(s)).")
        parties = [f"{date_fr} — {len(lignes)} marque(s) absent(s)/retard(s) :"]
        for l in lignes[:12]:
            nom = f"{l['prenom']} {l['nom']}".strip()
            parties.append(f"- {nom} ({l['classe'] or '?'}) : {l['statut']}"
                           + (f" — {l['motif']}" if l.get("motif") else ""))
        if len(lignes) > 12:
            parties.append(f"... et {len(lignes) - 12} autre(s).")
        parties.append(f"Present(s) ce jour : {nb_pres}.")
        return self._rep(
            "\n".join(parties),
            suggestions=["Qui est absent hier ?", "Moyenne de la classe",
                         "Solde de la caisse"])

    # ------------------------------------------------------------------
    # Questions : moyennes et notes
    # ------------------------------------------------------------------

    @staticmethod
    def _moyenne_matiere(note):
        d1, d2, comp = (note.get("devoir1"), note.get("devoir2"),
                        note.get("composition"))
        if d1 is None and d2 is None and comp is None:
            return None
        return ((d1 or 0) + (d2 or 0) + 2 * (comp or 0)) / 4.0

    def _generale_eleve(self, eleve_id, periode=None):
        sql = """SELECT n.*, m.nom AS matiere_nom, m.coefficient AS coeff
                 FROM notes n JOIN matieres m ON m.id = n.matiere_id
                 WHERE n.eleve_id = ?"""
        params = [eleve_id]
        if periode:
            sql += " AND n.periode = ?"
            params.append(periode)
        par_periode = {}
        for n in db.query(sql, params):
            moy = self._moyenne_matiere(n)
            if moy is None:
                continue
            tot = par_periode.setdefault(n["periode"], {"somme": 0.0, "coeffs": 0.0})
            tot["somme"] += moy * (n["coeff"] or 1)
            tot["coeffs"] += (n["coeff"] or 1)
        resultats = {p: round(tot["somme"] / tot["coeffs"], 2)
                     for p, tot in par_periode.items() if tot["coeffs"]}
        if periode:
            return resultats.get(periode)
        return resultats

    def _collecter_moyennes_globales(self):
        """Moyenne generale de chaque eleve note : renvoie une liste ORDONNEE
        [{prenom, nom, classe, classe_id, moyenne}] (la plus faible en 1er
        dans la liste, la meilleure en derniere position)."""
        lignes = []
        for e in repos.eleve.eleves():
            res = self._generale_eleve(e["id"])
            if not res:
                continue
            valeurs = list(res.values())
            if not valeurs:
                continue
            lignes.append({"prenom": e["prenom"], "nom": e["nom"],
                           "classe": e.get("classe_nom") or "?",
                           "classe_id": e.get("classe_id"),
                           "moyenne": round(sum(valeurs) / len(valeurs), 2)})
        lignes.sort(key=lambda x: x["moyenne"])
        return lignes

    def _moyenne_generale_texte(self):
        lignes = self._collecter_moyennes_globales()
        if not lignes:
            return None
        moy = round(sum(l["moyenne"] for l in lignes) / len(lignes), 2)
        meilleur = lignes[-1]
        en_queue = lignes[0]
        return (f"Moyenne generale de l'ecole : {moy:.2f}/20 "
                f"({appreciation(moy)}), sur {len(lignes)} eleve(s) note(s).\n"
                f"Meilleure moyenne : {meilleur['prenom']} {meilleur['nom']} "
                f"({meilleur['classe']}) avec {meilleur['moyenne']:.2f}."
                if len(lignes) >= 1 else f"Moyenne generale : {moy:.2f}/20")

    def _q_moyenne_generale(self, t):
        if not _contient_un(t, "moyenne generale", "moyenne de l ecole",
                            "moyenne des eleves", "moyenne de toutes les "
                            "classes", "moyenne de toute l ecole"):
            return None
        refus = self._verifier_acces("notes")
        if refus:
            return refus
        texte = self._moyenne_generale_texte()
        if texte is None:
            return self._rep("Aucune note enregistree : impossible de "
                             "calculer une moyenne generale.")
        moy = self._collecter_moyennes_globales()
        return self._rep(
            texte,
            explication=(f"J'ai calcule la moyenne generale ponderee de "
                         f"chaque eleve (formule (D1 + D2 + 2 x Composition) "
                         f"/ 4 par matiere, puis moyenne ponderee par les "
                         f"coefficients), puis la moyenne simple des "
                         f"{len(moy)} eleves notes."),
            suggestions=["Classement des eleves", "Moyenne de la classe 6eme",
                         "Solde de la caisse"])

    def _q_classement(self, t):
        if not _contient_un(t, "classement", "classer", "rang", "rangement",
                            "top", "meill", "pire"):
            return None
        refus = self._verifier_acces("notes")
        if refus:
            return refus
        classe = self._trouver_classe(t)
        if classe is not None:
            self._derniere_classe_id = classe["id"]
            lignes = [l for l in self._collecter_moyennes_globales()
                      if l["classe_id"] == classe["id"]]
            titre = f"Classement de la classe {classe['nom']} :"
            if not lignes:
                return self._rep(f"Aucune note enregistree pour classer la "
                                 f"classe {classe['nom']}.")
        else:
            lignes = self._collecter_moyennes_globales()
            titre = "Classement des eleves (toutes classes) :"
            if not lignes:
                return self._rep("Aucune note enregistree : je ne peux pas "
                                 "classer les eleves.")
        lignes_aff = list(reversed(lignes))
        parties = [titre]
        for i, l in enumerate(lignes_aff[:10], start=1):
            parties.append(f"{i}. {l['prenom']} {l['nom']} ({l['classe']}) : "
                           f"{l['moyenne']:.2f} ({appreciation(l['moyenne'])})")
        if len(lignes_aff) > 10:
            parties.append("(Top 10 affiche)")
        return self._rep(
            "\n".join(parties),
            explication=(f"J'ai trie les {len(lignes)} eleves selon leur "
                         f"moyenne generale ponderee (coefficients des "
                         f"matieres)."),
            suggestions=["Moyenne generale", "Moyenne de la classe 6eme",
                         "Qui est absent aujourd'hui ?"])

    def _q_moyennes(self, t):
        if not _contient_un(t, "moyenne", "moyennes", "resultat", "resultats",
                            "classement", "premier de la"):
            return None
        periode = self._extraire_periode(t)
        classe = self._trouver_classe(t)
        if classe is not None:
            refus = self._verifier_acces("notes")
            if refus:
                return refus
            self._derniere_classe_id = classe["id"]
            return self._moyennes_de_classe(classe, periode)
        eleve = self._trouver_eleve(t)
        if eleve is None and self._dernier_eleve_id and \
                not _contient_un(t, "classe"):
            eleve = repos.eleve.eleve_by_id(self._dernier_eleve_id)
        if eleve is None:
            return None
        refus = self._verifier_acces("notes")
        if refus:
            return refus
        self._dernier_eleve_id = eleve["id"]
        return self._moyennes_d_eleve(eleve, periode)

    def _moyennes_d_eleve(self, eleve, periode):
        nom_complet = f"{eleve['prenom']} {eleve['nom']}".strip()
        if periode:
            moy = self._generale_eleve(eleve["id"], periode=periode)
            if moy is None:
                return self._rep(f"Aucune note enregistree pour {nom_complet} "
                                 f"au {periode}.")
            return self._rep(f"Moyenne de {nom_complet} — {periode} : "
                             f"{moy:.2f}/20 ({appreciation(moy)}).")
        resultats = self._generale_eleve(eleve["id"])
        if not resultats:
            return self._rep(f"Aucune note enregistree pour {nom_complet}.")
        parties = [f"Moyennes de {nom_complet} :"]
        valeurs = []
        for p in PERIODES:
            if p in resultats:
                valeurs.append(resultats[p])
                parties.append(f"- {p} : {resultats[p]:.2f}/20 "
                               f"({appreciation(resultats[p])})")
        for p in sorted(set(resultats) - set(PERIODES)):
            valeurs.append(resultats[p])
            parties.append(f"- {p} : {resultats[p]:.2f}/20")
        if len(valeurs) > 1:
            globale = round(sum(valeurs) / len(valeurs), 2)
            parties.insert(1, f"> Moyenne annuelle : {globale:.2f}/20 "
                               f"({appreciation(globale)})")
        return self._rep(
            "\n".join(parties),
            explication=(f"J'ai calcule la moyenne generale de {nom_complet} : "
                         f"pour chaque matiere, formule (D1 + D2 + 2 x "
                         f"Composition) / 4, puis moyenne ponderee par les "
                         f"coefficients. Resultat final : "
                         f"{globale:.2f}/20." if len(valeurs) > 1
                         else f"J'ai calcule la moyenne de {nom_complet} pour "
                              f"{periode or 'la periode demandee'}."),
            suggestions=["Moyenne de la classe", "Combien d'eleves ?",
                         "Qui est absent aujourd'hui ?"])

    def _moyennes_de_classe(self, classe, periode):
        eleves = repos.eleve.eleves(classe_id=classe["id"])
        if not eleves:
            return self._rep(f"Aucun eleve dans la classe {classe['nom']}.")
        lignes = []
        for e in eleves:
            res = self._generale_eleve(e["id"], periode=periode)
            if res is None:
                continue
            if isinstance(res, dict):
                # Pas de periode demandee : moyenne des trimestres notes.
                if not res:
                    continue
                valeurs = list(res.values())
                res = round(sum(valeurs) / len(valeurs), 2)
            lignes.append((res, e["prenom"], e["nom"]))
        if not lignes:
            suffixe = f" au {periode}" if periode else ""
            return self._rep(f"Aucune note enregistree pour la classe "
                             f"{classe['nom']}{suffixe}.")
        lignes.sort(key=lambda x: x[0], reverse=True)
        titre = f"Classe {classe['nom']}" + (f" — {periode}" if periode else "")
        parties = [f"{titre} — {len(lignes)} eleve(s) note(s) :"]
        for rang, (moy, prenom, nom) in enumerate(lignes[:10], start=1):
            parties.append(f"{rang}. {prenom} {nom} : {moy:.2f} "
                           f"({appreciation(moy)})")
        moyenne_classe = round(sum(m for m, _, _ in lignes) / len(lignes), 2)
        parties.append(f"> Moyenne de la classe : {moyenne_classe:.2f}/20 "
                       f"({appreciation(moyenne_classe)})")
        if len(lignes) > 10:
            parties.append("(Top 10 affiche)")
        return self._rep(
            "\n".join(parties),
            explication=(f"Pour chaque eleve, j'ai calcule la moyenne "
                         f"generale ponderee (coefficients des matieres). "
                         f"Puis j'ai moyenne simple de {len(lignes)} eleves = "
                         f"{moyenne_classe:.2f}. Formule par matiere : "
                         f"(D1 + D2 + 2 x Composition) / 4."),
            suggestions=["Moyenne de " + self._nom_dernier_eleve(),
                         "Qui est absent aujourd'hui ?", "Solde de la caisse"])

    @staticmethod
    def _extraire_periode(t):
        motifs = [
            (("1er trimestre", "premier trimestre", "trim 1"), PERIODES[0]),
            (("2eme trimestre", "deuxieme trimestre", "trim 2"), PERIODES[1]),
            (("3eme trimestre", "troisieme trimestre", "trim 3"), PERIODES[2]),
        ]
        for chaines, periode in motifs:
            if any(ch in t for ch in chaines) or \
                    re.search(rf"trimestre\s*{periode[0]}\b", t):
                return periode
        return None

    # ------------------------------------------------------------------
    # Questions : paiements d'un eleve
    # ------------------------------------------------------------------

    def _q_paiements_globale(self, t):
        """Vue globale des paiements (mois courant, meilleurs/moins bons
        payeurs) quand aucune eleve n'est vise."""
        mois_courant = "mois" in t or "ce mois" in t
        classement = _contient_un(t, "le moins", "le plus",
                                  "mieux paye", "mieux payer",
                                  "classement des paiements",
                                  "qui paie le moins", "qui a le plus paye",
                                  "qui a le mieux paye")
        if not mois_courant and not classement:
            return None
        if mois_courant:
            annee, mois = datetime.date.today().strftime("%Y-%m").split("-")
            paiements = db.query(
                """SELECT p.montant, e.prenom, e.nom
                   FROM paiements p JOIN eleves e ON e.id = p.eleve_id
                   WHERE substr(p.date_paiement, 1, 7) = ?""",
                (f"{annee}-{mois}",))
            total = sum((p["montant"] or 0) for p in paiements)
            texte = (f"Paiements du mois en cours : {len(paiements)} "
                     f"versement(s) pour {formater_fcfa(total)}.")
            if paiements:
                par = {}
                for p in paiements:
                    nom = f"{p['prenom']} {p['nom']}".strip()
                    par[nom] = par.get(nom, 0) + (p["montant"] or 0)
                top = sorted(par.items(), key=lambda kv: kv[1], reverse=True)[:5]
                texte += "\nTop payeurs du mois : " + "; ".join(
                    f"{n} ({formater_fcfa(m)})" for n, m in top)
            return self._rep(
                texte,
                suggestions=["Qui a le plus paye ?", "Solde de la caisse",
                             "Combien d'eleves ?"])
        if classement:
            par = {}
            for p in db.query(
                    """SELECT p.montant, e.prenom, e.nom
                       FROM paiements p JOIN eleves e ON e.id = p.eleve_id"""):
                nom = f"{p['prenom']} {p['nom']}".strip()
                par[nom] = par.get(nom, 0) + (p["montant"] or 0)
            if not par:
                return self._rep("Aucun paiement enregistre jusqu'ici.")
            rangs = sorted(par.items(), key=lambda kv: kv[1])
            plus = rangs[-1]
            moins = rangs[0]
            texte = (f"Qui a le plus paye : {plus[0]} "
                     f"({formater_fcfa(plus[1])}) sur {len(par)} payeur(s).\n")
            if len(rangs) > 1 or plus[0] != moins[0]:
                texte += (f"Versements les plus faibles : {moins[0]} "
                          f"({formater_fcfa(moins[1])}).")
            else:
                texte += "Un seul eleve a paye jusqu'ici."
            return self._rep(
                texte,
                suggestions=["Combien ont paye ce mois ?",
                             "Paiements de " + self._nom_dernier_eleve(),
                             "Solde de la caisse"])

    def _q_paiements_eleve(self, t):
        if not _contient_un(t, "paye", "payer", "paiement", "paiements",
                            "versement", "reste a payer"):
            return None
        if self._verifier_acces("paiements"):
            return self._verifier_acces("paiements")
        if _contient_un(t, "caisse", "tous les paiements", "total des paiements"):
            return None
        eleve = self._trouver_eleve(t)
        if eleve is None and self._dernier_eleve_id:
            eleve = repos.eleve.eleve_by_id(self._dernier_eleve_id)
        if eleve is None:
            return self._q_paiements_globale(t)
        self._dernier_eleve_id = eleve["id"]
        paiements = repos.finance.paiements(nom=eleve["nom"], prenom=eleve["prenom"])
        total_paye = sum(p["montant"] or 0 for p in paiements)
        nom_complet = f"{eleve['prenom']} {eleve['nom']}".strip()
        texte = [f"{nom_complet} ({eleve['matricule']}) — classe "
                 f"{eleve.get('classe_nom') or 'non affectee'} :",
                 f"- Total paye : {formater_fcfa(total_paye)} "
                 f"({len(paiements)} paiement(s))"]
        tarifs = repos.finance.tarifs(classe_id=eleve["classe_id"]) \
            if eleve["classe_id"] else []
        total_du = sum(tr["montant"] or 0 for tr in tarifs)
        if total_du:
            reste = total_du - total_paye
            if reste > 0:
                texte.append(f"- Reste a payer : {formater_fcfa(reste)} "
                             f"(sur {formater_fcfa(total_du)} de frais prevus)")
            else:
                texte.append(f"- Frais prevus : {formater_fcfa(total_du)} -> "
                             f"solde honore"
                             + (f" (excedent : {formater_fcfa(-reste)})"
                                if reste < 0 else ""))
        if paiements:
            dernier = max(paiements, key=lambda p: (p["date_paiement"], p["id"]))
            texte.append(f"- Dernier versement : "
                         f"{formater_fcfa(dernier['montant'])} le "
                         f"{formater_date(dernier['date_paiement'])} "
                         f"({dernier.get('type_frais') or '-'})")
        return self._rep(
            "\n".join(texte),
            explication=(f"J'ai additionne tous les paiements de "
                         f"{nom_complet} ({total_paye:.0f} FCFA sur "
                         f"{len(paiements)} paiement(s)). Frais prevus de la "
                         f"classe : {total_du:.0f} FCFA. Reste a payer : "
                         f"{reste:.0f} FCFA." if total_du
                         else f"J'ai additionne {len(paiements)} paiement(s) "
                              f"pour {nom_complet} : {total_paye:.0f} FCFA."),
            suggestions=["Moyenne de " + self._nom_dernier_eleve(),
                         "Fiche de " + self._nom_dernier_eleve(),
                         "Tarifs de la classe"])

    # ------------------------------------------------------------------
    # Questions : tarifs d'une classe
    # ------------------------------------------------------------------

    def _q_tarifs_classe(self, t):
        if not _contient_un(t, "tarif", "tarifs", "frais", "cout", "couts",
                            "prix", "coute"):
            return None
        if self._verifier_acces("tarifs"):
            return self._verifier_acces("tarifs")
        classe = self._trouver_classe(t)
        if classe is None:
            return None
        self._derniere_classe_id = classe["id"]
        tarifs = repos.finance.tarifs(classe_id=classe["id"])
        if not tarifs:
            return self._rep(f"Aucun tarif defini pour la classe "
                             f"{classe['nom']}.")
        parties = [f"Tarifs de la classe {classe['nom']} :"]
        total = 0.0
        for tr in tarifs:
            total += tr["montant"] or 0
            annee = f" ({tr['annee_scolaire']})" if tr.get("annee_scolaire") else ""
            parties.append(f"- {tr['type_frais']} : "
                           f"{formater_fcfa(tr['montant'])}{annee}")
        parties.append(f"> TOTAL des frais : {formater_fcfa(total)}")
        return self._rep("\n".join(parties))

    # ------------------------------------------------------------------
    # Questions : caisse
    # ------------------------------------------------------------------

    def _q_caisse(self, t):
        if not _contient_un(t, "caisse", "solde", "tresorerie", "entree",
                            "sortie", "recette", "depense", "transaction",
                            "argent", "finance"):
            return None
        if self._verifier_acces("caisse"):
            return self._verifier_acces("caisse")
        entree, sortie, solde = repos.finance.caisse_totals()

        if _contient_un(t, "dernier", "recente", "recentes", "recents",
                        "mouvement", "journal", "liste"):
            lignes = repos.finance.transactions()[:8]
            if not lignes:
                return self._rep("Aucune transaction enregistree.")
            parties = ["Dernieres transactions :"]
            for tr in lignes:
                signe = "+" if tr["type"] == "entree" else "-"
                parties.append(
                    f"- {formater_date(tr['date'])} "
                    f"{signe}{formater_fcfa(tr['montant'])} — "
                    f"{tr['motif'] or tr['beneficiaire'] or '?'} "
                    f"[{tr['reference']}]")
            parties.append(f"Solde actuel : {formater_fcfa(solde)}")
            return self._rep(
                "\n".join(parties),
                explication=(f"J'ai recupere les {len(lignes)} dernieres "
                             f"transactions de la caisse et calcule le solde "
                             f"(entrees - sorties = {solde:.0f} FCFA)."),
                suggestions=["Solde de la caisse", "Enregistrer une entree",
                             "Combien d'eleves ?"])

        texte = (f"Caisse — Entrees : {formater_fcfa(entree)} | Sorties : "
                 f"{formater_fcfa(sortie)} | SOLDE : {formater_fcfa(solde)}.")
        if solde < 0:
            texte += "\nAttention : solde negatif !"
        return self._rep(
            texte,
            explication=(f"Solde = entrees ({entree:.0f} FCFA) - sorties "
                         f"({sortie:.0f} FCFA) = {solde:.0f} FCFA."),
            suggestions=["Dernieres transactions", "Masse salariale",
                         "Enregistrer une entree de 5000 pour fournitures"])

    # ------------------------------------------------------------------
    # Questions : personnel
    # ------------------------------------------------------------------

    def _q_personnel(self, t):
        if not _contient_un(t, "personnel", "enseignant", "enseignants",
                            "professeur", "professeurs", "instituteur",
                            "masse salariale", "salaire", "salaires", "employe"):
            return None
        if self._verifier_acces("personnel"):
            return self._verifier_acces("personnel")
        tout = repos.personnel_repo.personnel()
        if not tout:
            return self._rep("Aucun membre du personnel enregistre.")
        if _contient_un(t, "masse salariale", "salaire", "salaires"):
            masse = repos.personnel_repo.masse_salariale()
            return self._rep(f"Masse salariale mensuelle : {formater_fcfa(masse)} "
                             f"pour {len(tout)} membre(s) du personnel.")
        profs = [p for p in tout if _contient_un(
            normaliser(p.get("fonction") or ""), "enseign", "professeur",
            "instit")]
        if _contient_un(t, "enseignant", "enseignants", "professeur",
                        "professeurs", "instit"):
            if not profs:
                return self._rep("Aucun enseignant trouve dans le personnel.")
            parties = [f"{len(profs)} enseignant(s) :"]
            for p in profs[:12]:
                parties.append(f"- {p['nom_complet']} — {p['fonction']} "
                               f"({formater_fcfa(p['salaire'])})")
            return self._rep("\n".join(parties))
        return self._rep(f"Personnel : {len(tout)} membres dont "
                         f"{len(profs)} enseignant(s).")

    # ------------------------------------------------------------------
    # Questions : annee active
    # ------------------------------------------------------------------

    def _q_annee_active(self, t):
        if not _contient_un(t, "annee", "rentree"):
            return None
        if _contient_un(t, "moyenne", "note", "paye", "absent", "naissance",
                        "ne le", "age"):
            return None
        active = repos.classe.annee_scolaire_active()
        if not active:
            return self._rep("Aucune annee scolaire active ! Definissez-en "
                             "une dans CYCLES & ANNEES sinon certaines saisies "
                             "seront bloquees.",
                             action={"type": "navigate", "page": "cycles"})
        texte = (f"Annee scolaire active : {active['libelle']} "
                 f"(du {formater_date(active['date_debut'])} au "
                 f"{formater_date(active['date_fin'])}).")
        if _contient_un(t, "combien", "liste", "toutes", "autres"):
            toutes = repos.classe.annees_scolaires()
            texte += "\nAnnees connues : " + \
                ", ".join(a["libelle"] for a in toutes)
        return self._rep(texte)

    # ------------------------------------------------------------------
    # Questions : fiche eleve
    # ------------------------------------------------------------------

    def _q_fiche_eleve(self, t):
        if not _contient_un(t, "qui est", "fiche", "info", "information",
                            "cherche", "trouve", "contact", "parent",
                            "telephone", "naissance", "matricule", "age"):
            return None
        eleve = self._trouver_eleve(t)
        if eleve is None:
            return None
        refus = self._verifier_acces("eleves")
        if refus:
            return refus
        self._dernier_eleve_id = eleve["id"]
        return self._fiche_reponse(eleve)

    def _fiche_reponse(self, eleve):
        sexe = {"M": "Garcon", "F": "Fille"}.get(eleve.get("sexe"), "?")
        parties = [f"FICHE ELEVE — {eleve['prenom']} {eleve['nom']}",
                   f"- Matricule : {eleve['matricule']}",
                   f"- Sexe : {sexe} | Statut : {eleve.get('statut') or '?'}",
                   f"- Classe : {eleve.get('classe_nom') or 'non affectee'}"]
        if eleve.get("date_naissance"):
            parties.append(f"- Ne(e) le {formater_date(eleve['date_naissance'])}"
                           + (f" a {eleve['lieu_naissance']}"
                              if eleve.get("lieu_naissance") else ""))
        contacts = []
        if eleve.get("pere_nom"):
            contacts.append(f"Pere : {eleve['pere_nom']} "
                            f"{eleve.get('pere_tel') or ''}".strip())
        if eleve.get("mere_nom"):
            contacts.append(f"Mere : {eleve['mere_nom']} "
                            f"{eleve.get('mere_tel') or ''}".strip())
        if eleve.get("tuteur_nom"):
            contacts.append(f"Tuteur : {eleve['tuteur_nom']} "
                            f"{eleve.get('tuteur_tel') or ''}".strip())
        if contacts:
            parties.append("- " + " | ".join(contacts))
        parties.append("(Double-cliquez sur l'eleve dans ELEVES pour la fiche "
                       "complete)")
        return self._rep("\n".join(parties))

    # ------------------------------------------------------------------
    # Questions : effectifs
    # ------------------------------------------------------------------

    def _q_effectifs(self, t):
        if not _contient_un(t, "combien", "nombre", "effectif", "effectifs",
                            "total"):
            return None
        if not _contient_un(t, "eleve", "eleves", "fille", "filles", "garcon",
                            "garcons", "classe", "classes"):
            return None
        if self._verifier_acces("eleves"):
            return self._verifier_acces("eleves")

        filtre_sexe = None
        if _contient_un(t, "fille", "filles"):
            filtre_sexe = "F"
        elif _contient_un(t, "garcon", "garcons"):
            filtre_sexe = "M"

        classe = self._trouver_classe(t)
        if classe is not None:
            self._derniere_classe_id = classe["id"]
            eleves = repos.eleve.eleves(classe_id=classe["id"])
            nb = len(eleves)
            filles = sum(1 for e in eleves if e.get("sexe") == "F")
            capacite = classe.get("capacite") or 50
            taux = round(nb * 100.0 / capacite) if capacite else 0
            detail_sexe = f" ({filles} fille(s), {nb - filles} garcon(s))"
            if filtre_sexe == "F":
                return self._rep(f"Classe {classe['nom']} : {filles} fille(s) "
                                 f"sur {nb} eleve(s).")
            if filtre_sexe == "M":
                return self._rep(f"Classe {classe['nom']} : {nb - filles} "
                                 f"garcon(s) sur {nb} eleve(s).")
            return self._rep(f"Classe {classe['nom']} : {nb} eleve(s)"
                             f"{detail_sexe} — remplissage {taux}% de la "
                             f"capacite ({capacite} places).")

        for cyc in repos.classe.cycles():
            if normaliser(cyc["nom"]) in t:
                total = db.query(
                    """SELECT COUNT(*) AS c FROM eleves e
                       JOIN classes cl ON cl.id = e.classe_id
                       WHERE cl.cycle_id = ?""", (cyc["id"],))
                return self._rep(f"Cycle {cyc['nom']} : {total[0]['c']} "
                                 "eleve(s) toutes classes confondues.")

        tous = repos.eleve.eleves()
        nb_total = len(tous)
        filles = sum(1 for e in tous if e.get("sexe") == "F")
        garcons = nb_total - filles
        inscrits = sum(1 for e in tous if (e.get("statut") or "") == "Inscrit")
        if filtre_sexe == "F":
            return self._rep(f"L'ecole compte {filles} fille(s) sur "
                             f"{nb_total} eleve(s) enregistre(s).",
                             suggestions=["Combien de garcons ?", "Moyenne de la classe 6eme"])
        if filtre_sexe == "M":
            return self._rep(f"L'ecole compte {garcons} garcon(s) sur "
                             f"{nb_total} eleve(s) enregistre(s).",
                             suggestions=["Combien de filles ?", "Moyenne de la classe 6eme"])
        return self._rep(
            f"Effectif total : {nb_total} eleve(s) enregistre(s) — {filles} "
            f"fille(s), {garcons} garcon(s), dont {inscrits} au statut "
            f"« Inscrit ».\nDemandez une classe precise : « combien d'eleves "
            f"en 6eme ? »",
            explication=(f"J'ai compte tous les eleves de la table principale. "
                         f"Resultat : {nb_total} au total, {filles} filles, "
                         f"{garcons} garcons, {inscrits} inscrits."),
            suggestions=["Combien de filles ?", "Combien de garcons ?",
                         "Qui est absent aujourd'hui ?"])

    # ------------------------------------------------------------------
    # Recherche d'entites (floue)
    # ------------------------------------------------------------------

    def _trouver_classe(self, t):
        classes = repos.classe.classes()
        if not classes:
            return None
        mots_t = [w for w in t.split() if w not in _MOTS_VIDES and len(w) >= 2]
        meilleure, meilleur_score = None, 0.0
        for c in classes:
            nom_norm = normaliser(c["nom"])
            if nom_norm and nom_norm in t:
                return c
            score = SequenceMatcher(None, nom_norm, t).ratio()
            score_ngram = similarite(nom_norm, t)
            score = max(score, score_ngram * 0.8)
            for tok_nom in nom_norm.split():
                for tok_t in mots_t:
                    if tok_nom == tok_t or (len(tok_nom) >= 3 and
                                            tok_nom.startswith(tok_t)):
                        score = max(score, 0.85)
            if score > meilleur_score:
                meilleure, meilleur_score = c, score
        return meilleure if meilleur_score >= 0.72 else None

    def _trouver_eleve(self, t):
        eleves = repos.eleve.eleves()
        if not eleves:
            return None
        candidates = []
        for e in eleves:
            nom_complet = normaliser(f"{e['nom']} {e['prenom']}")
            nom_inverse = normaliser(f"{e['prenom']} {e['nom']}")
            if nom_complet in t or nom_inverse in t:
                candidates.append((1.0, e))
                continue
            score = max(SequenceMatcher(None, nom_complet, t).ratio(),
                        SequenceMatcher(None, nom_inverse, t).ratio())
            score_ngram = max(similarite(nom_complet, t), similarite(nom_inverse, t))
            score = max(score, score_ngram * 0.85)
            tokens_nom = set(nom_complet.split())
            for tok in t.split():
                if tok in tokens_nom:
                    score = max(score, 0.9)
                elif len(tok) >= 4:
                    for tn in tokens_nom:
                        if tn.startswith(tok[:4]):
                            score = max(score, 0.78)
            if score >= 0.68:
                candidates.append((score, e))
        if not candidates:
            return None
        candidates.sort(key=lambda pair: pair[0], reverse=True)
        return candidates[0][1]

    def _chips_eleves(self, limite=4):
        try:
            eleves = repos.eleve.eleves()[:limite]
            return [f"Moyenne de {e['prenom']} {e['nom']}" for e in eleves]
        except Exception:
            return []

    def _secours_flou(self, t):
        if len(t.split()) > 6:
            return None
        eleve = self._trouver_eleve(t)
        if eleve is not None:
            self._dernier_eleve_id = eleve["id"]
            return self._fiche_reponse(eleve)
        classe = self._trouver_classe(t)
        if classe is not None:
            self._derniere_classe_id = classe["id"]
            return self._rep(
                f"Vous parlez de la classe {classe['nom']} ? Elle compte "
                f"{classe.get('effectif', '?')} eleve(s). Essayez : « combien "
                f"d'eleves en {classe['nom']} », « tarifs de {classe['nom']} » "
                f"ou « moyenne de la classe ».")
        return None

    # ------------------------------------------------------------------
    # Lecture des donnees (index semantique sur la base)
    # ------------------------------------------------------------------

    def _chercher_dans_donnees(self, t):
        import time
        maintenant = time.time()
        if self._corpus_date == 0.0 or \
                maintenant - self._corpus_date > self.TTL_CORPUS:
            self._construire_corps_donnees()
            self._corpus_date = maintenant
        resultat = self._index_donnees.rechercher(t, seuil=_SEUIL_CORPUS)
        if resultat is None:
            return None
        _, texte = resultat
        return self._rep("(Lu directement dans les donnees de l'ecole)\n"
                         + texte, source="corpus")

    def _construire_corps_donnees(self):
        idx = self._index_donnees
        idx.vider()

        for c in repos.classe.classes():
            idx.ajouter(
                f"La classe {c['nom']} appartient au cycle "
                f"{c.get('cycle_nom') or 'non defini'}, effectif "
                f"{c.get('effectif', 0)} eleve(s), capacite "
                f"{c.get('capacite') or 50}, salle {c.get('salle') or 'non '
                'renseignee'}, titulaire {c.get('titulaire') or 'non designe'}.")

        for e in repos.eleve.eleves():
            sexe = {"M": "masculin", "F": "feminin"}.get(e.get("sexe"), "?")
            idx.ajouter(
                f"L'eleve {e['prenom']} {e['nom']}, matricule {e['matricule']}, "
                f"est en classe {e.get('classe_nom') or 'non affectee'}, "
                f"statut {e.get('statut') or '?'}, sexe {sexe}.")

        for tr in repos.finance.transactions()[:60]:
            idx.ajouter(
                f"Transaction {tr['reference']} du {formater_date(tr['date'])} : "
                f"{tr['type']} de {formater_fcfa(tr['montant'])}, motif "
                f"{tr['motif'] or 'non precise'}, beneficiaire "
                f"{tr['beneficiaire'] or 'non precise'}.")

        for tr in repos.finance.tarifs():
            idx.ajouter(
                f"Tarif {tr['type_frais']} de la classe "
                f"{tr.get('classe_nom') or '?'} : {formater_fcfa(tr['montant'])}.")

        try:
            for p in repos.personnel_repo.personnel():
                idx.ajouter(
                    f"{p['nom_complet']} fait partie du personnel comme "
                    f"{p.get('fonction') or 'agent'}, salaire "
                    f"{formater_fcfa(p.get('salaire'))}.")
        except Exception:
            pass

        idx.construire()

    # ------------------------------------------------------------------
    # Aide
    # ------------------------------------------------------------------

    def _aide(self):
        return self._rep(
            f"Voici ce que je sais faire ({NOM_ASSISTANT}) :\n"
            "RENSEIGNER — « combien d'eleves ? », « combien en 6eme ? », "
            "« qui est absent aujourd'hui ? », « solde de la caisse », "
            "« dernieres transactions », « moyenne de <eleve> », « moyenne de "
            "la classe 6eme », « combien a paye <eleve> », « tarifs de la "
            "classe CM2 », « masse salariale », « quelle annee est active ? »\n"
            "CALCULER — « 125000 - 45000 », moyennes ponderees automatiques\n"
            "CREER — « creer un cycle Superieur », « creer une matiere "
            "Histoire coefficient 2 », « creer une classe 6eme B », "
            "« enregistrer une entree de 5000 pour fournitures », « inscrire "
            "un nouvel eleve »\n"
            "OUVRIR — « ouvre les paiements », « va a la caisse »\n"
            "APPRENDRE — « retiens que ... », « quand je dis X reponds Y », "
            "« montre ta memoire », « oublie ... »\n"
            "EXPLIQUER — « explique-moi », « comment tu as calculé ? » "
            "(je detaillerai mon raisonnement)\n"
            "COMPOSE — « X et Y ? » (je reponds aux deux questions)\n"
            "MULTI-POSTES — « etat du serveur », « synchronise maintenant »\n"
            "MANUEL — « comment inscrire un eleve ? », « comment faire les "
            "bulletins ? », « comment sauvegarder ? »\n"
            "AUTO-APPRENTISSAGE — « tes statistiques », « ameliore-toi »\n"
            "(pour chaque reponse, vous pouvez noter 👍 / 👎 : je m'en sers "
            "pour renforcer ou corriger ma memoire)",
            choix=self.suggestions())

    def _forme_stats(self):
        """Presse-citron lisible des statistiques d'apprentissage."""
        stats = self._apprentissage.statistiques()
        if (stats["feedback_pos"] + stats["feedback_neg"]) == 0:
            avis = "Aucun retour de votre part encore. Utilisez les boutons " \
                   "👍 / 👎 sous mes reponses pour m'aider a apprendre."
        else:
            taux = round(100.0 * stats["feedback_pos"] /
                         (stats["feedback_pos"] + stats["feedback_neg"]))
            avis = f"Taux d'approbation de vos retours : {taux}%."
        return (f"Ma memoire ({NOM_ASSISTANT}) :\n"
                f"- {stats['total_questions']} question(s) posee(s) ;\n"
                f"- {stats['apprentissages']} souvenir(s) en memoire durable, "
                f"- {stats['rejeux']} rejeu(x) enregistre(s) ;\n"
                f"- {stats['feedback_pos']} avis positif(s), "
                f"{stats['feedback_neg']} negatif(s) ;\n"
                f"- {stats['entrainements']} passe(s) d'auto-amelioration ;\n"
                f"- {stats['journal']} tour(s) gardes en trace.\n{avis}\n"
                f"Je m'auto-ameliore automatiquement : je fusionne mes "
                f"doublons, nettoie mes apprentissages abandonnes et "
                f"corrige les reponses mal notees.")

    def noter_reponse(self, note, motif=None):
        """Feedback public : note=1 (bonne reponse) / note=-1 (mauvaise).

        Retourne la reponse de remerciement de l'assistante.
        """
        question = self._derniere_question_brute or ""
        reponse_texte = (self._derniere_reponse or {}).get("texte") or ""
        try:
            modifie = self._apprentissage.noter(question, reponse_texte,
                                                int(note), motif)
        except Exception:
            modifie = 0
        if int(note) > 0:
            merci = f"Merci ! Je renforce cette reponse dans ma memoire." if modifie \
                else "Merci ! Je garde cette interaction en trace."
            return self._rep(merci, source="feedback")
        conseil = ("Je note avec attention et je vais m'ameliorer. Vous "
                   "pouvez m'apprendre directement la bonne reponse : "
                   "« retiens que ... » ou cliquez « Apprendre la bonne "
                   "reponse ».")
        if modifie:
            conseil += " J'ai deja baisse la confiance de la reponse fautive."
        return self._rep(conseil, source="feedback",
                         choix=["Apprendre la bonne reponse"])

    def ameliorer(self, force=False):
        """Passe d'entrainement manuel (retourne un rapport)."""
        try:
            return self._apprentissage.ameliorer(force=force)
        except Exception:
            return {"fusionne": 0, "retires": 0, "rejouee": 0, "memoire": 0,
                    "journal": 0, "publicite": True}

    def statistiques(self):
        """Statistiques d'apprentissage (dict)."""
        self._apprentissage.ensure_tables()
        return self._apprentissage.statistiques()
