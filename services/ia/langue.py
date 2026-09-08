"""Traitement de langue francaise leger (stdlib uniquement).

Pipeline : sans_accents -> tokenisation -> distance Damerau-Levenshtein
(bornee) -> correction contre un vocabulaire -> similarite en n-grammes
de caracteres pour les rapprochements flous.

Concu pour de tres petits corpus (quelques centaines de mots) : tout est
en O(n*m) borne, aucune dependance externe, demarrage instantane.
"""

import re
import unicodedata

_MOT = re.compile(r"[^\W\d_]+|\d+[^\W\d_]+", re.UNICODE)
_TOKEN = re.compile(r"[a-z0-9]+")

# Mots-outils francais courants jamais modifies par la correction.
# Sans cette liste, « entre » (preposition) devenait « entree » (vocab).
_MOTS_NEUTRES = frozenset({
    "a", "ai", "au", "aux", "avec", "c", "ca", "ce", "ces", "comme",
    "comment", "dans", "de", "des", "du", "elle", "en", "entre", "et",
    "il", "je", "la", "le", "les", "leur", "lui", "mais", "me", "mes",
    "mieux", "mon", "ne", "nous", "ou", "par", "pas", "pour", "que",
    "quel", "quelle", "quelque", "quels", "qui", "sa", "se", "ses",
    "son", "sur", "ta", "te", "tes", "toi", "ton", "toujours", "tout",
    "tous", "tu", "un", "une", "vous", "y",
})


def sans_accents(texte):
    """« Élève » -> « eleve » (NFKD puis suppression des diacritiques)."""
    decompose = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in decompose if not unicodedata.combining(c))


def normaliser(texte):
    """Minuscules + sans accents + espaces compactes."""
    t = sans_accents((texte or "").lower())
    return re.sub(r"\s+", " ", t).strip()


def tokeniser(texte):
    return _TOKEN.findall(sans_accents((texte or "").lower()))


def damerau(a, b, plafond=None):
    """Distance Damerau-Levenshtein (substitutions, insertions,
    suppressions, transpositions de paires).

    plafond : coupe prematurement si la distance depasse cette valeur
    (retourne alors plafond + 1) — indispensable pour rester rapide sur
    un vocabulaire de plusieurs centaines d'entrees."""
    la, lb = len(a), len(b)
    if plafond is not None and abs(la - lb) > plafond:
        return plafond + 1
    precedent_precedent = None
    precedent = list(range(lb + 1))
    for i in range(1, la + 1):
        courant = [i] + [0] * lb
        meilleur_ligne = i
        for j in range(1, lb + 1):
            cout = 0 if a[i - 1] == b[j - 1] else 1
            v = min(precedent[j] + 1,          # suppression
                    courant[j - 1] + 1,        # insertion
                    precedent[j - 1] + cout)   # substitution
            if (i > 1 and j > 1 and a[i - 1] == b[j - 2]
                    and a[i - 2] == b[j - 1]):
                v = min(v, precedent_precedent[j - 2] + 1)  # transposition
            courant[j] = v
            if v < meilleur_ligne:
                meilleur_ligne = v
        if plafond is not None and meilleur_ligne > plafond:
            return plafond + 1
        precedent_precedent = precedent
        precedent = courant
    return precedent[lb]


def _seuil(longueur):
    if longueur <= 3:
        return 0
    if longueur <= 5:
        return 1
    return 2


def corriger_mot(mot, vocabulaire):
    """Renvoie le mot du vocabulaire le plus proche, ou le mot intact.

    Garde-fous anti-corrections absurdes :
    - jamais de correction des mots courts (<= 3) ni des nombres ;
    - mots-outils francais jamais modifies (prepositions, articles...) ;
    - distance 2 exige la meme initiale + 2 lettres de debut identiques."""
    base = sans_accents(mot).lower()
    if base in vocabulaire or len(base) <= 3 or base.isdigit():
        return mot
    if base in _MOTS_NEUTRES:
        return mot
    seuil = _seuil(len(base))
    meilleur, meilleure_dist = None, seuil + 1
    for candidat in vocabulaire:
        if abs(len(candidat) - len(base)) > seuil:
            continue
        dist = damerau(base, candidat, plafond=seuil)
        if dist < meilleure_dist:
            meilleur, meilleure_dist = candidat, dist
            if dist == 0:
                break
    if meilleur is None or meilleure_dist > seuil:
        return mot
    if meilleure_dist == 2 and (meilleur[:2] != base[:2] or len(base) < 6):
        return mot
    return meilleur


def corriger_phrase(texte, vocabulaire):
    """Corrige chaque mot alphabetique inconnu, sans toucher au reste
    (chiffres, ponctuation, majuscules preservees sur les mots connus)."""
    vocabulaire_norm = {sans_accents(v).lower() for v in vocabulaire}

    def _remplace(m):
        mot = m.group(0)
        if mot.isdigit():
            return mot
        return corriger_mot(mot, vocabulaire_norm)

    return _MOT.sub(_remplace, texte)


# ----------------------------------------------------------------------
# Similarite par n-grammes de caracteres (robuste aux petites fautes
# meme hors vocabulaire : noms propres inconnus, abreviations...)
# ----------------------------------------------------------------------

def _ngrammes(chaine, n=3):
    c = f"  {normaliser(chaine)}  "
    if len(c) < n:
        return {c} if c else set()
    return {c[i:i + n] for i in range(len(c) - n + 1)}


def similarite(a, b):
    """Coefficient de Dice entre n-grammes : 1.0 identique, 0.0 aucun lien."""
    ga, gb = _ngrammes(a), _ngrammes(b)
    if not ga or not gb:
        return 0.0
    commun = len(ga & gb)
    return 2.0 * commun / (len(ga) + len(gb))
