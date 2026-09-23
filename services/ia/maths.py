"""Calculatrice sure : francais naturel -> AST -> evaluation blanche.

AUCUN eval() : l'expression est parsee par ast.parse puis chaque noeud
est valide contre une liste blanche (operations arithmetiques, constantes
pi/e, fonctions statistiques). Tout le reste est refuse.

Exemples acceptes :
  « 125000 - 45000 »          « calcule 20% de 500000 »
  « racine carree de 144 »    « (12+8)x3 / 5 »
  « moyenne de 12 14 16 »     « mediane de 8, 15, 9 »
  « ecart type de 10 12 14 »  « 2 puissance 10 »
"""

import ast
import math
import operator
import re


class ErreurCalcul(ValueError):
    """Erreur metier affichable a l'utilisateur."""


# --- liste blanche d'operations ---------------------------------------

_OPS_BIN = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_OPS_UNA = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_CONSTANTES = {"pi": math.pi, "e": math.e}

_LIMITES = {
    "exposant_max": 32,
    "base_max": 1e15,
    "longueur_expr": 160,
}


def _moyenne(valeurs):
    valeurs = _verifier_liste(valeurs)
    return sum(valeurs) / len(valeurs)


def _mediane(valeurs):
    valeurs = sorted(_verifier_liste(valeurs))
    n = len(valeurs)
    milieu = n // 2
    if n % 2:
        return valeurs[milieu]
    return (valeurs[milieu - 1] + valeurs[milieu]) / 2


def _ecart_type(valeurs):
    valeurs = _verifier_liste(valeurs)
    if len(valeurs) < 2:
        raise ErreurCalcul("L'ecart type demande au moins deux valeurs.")
    m = sum(valeurs) / len(valeurs)
    variance = sum((v - m) ** 2 for v in valeurs) / (len(valeurs) - 1)
    return math.sqrt(variance)


def _variance(valeurs):
    valeurs = _verifier_liste(valeurs)
    if len(valeurs) < 2:
        raise ErreurCalcul("La variance demande au moins deux valeurs.")
    m = sum(valeurs) / len(valeurs)
    return sum((v - m) ** 2 for v in valeurs) / (len(valeurs) - 1)


def _verifier_liste(valeurs):
    if not valeurs or len(valeurs) > 64:
        raise ErreurCalcul("Donnez entre 1 et 64 nombres.")
    for v in valeurs:
        if abs(v) > _LIMITES["base_max"]:
            raise ErreurCalcul("Nombre trop grand.")
    return valeurs


_FONCTIONS = {
    "sqrt": math.sqrt, "racine": math.sqrt, "racinecarree": math.sqrt,
    "abs": abs, "arrondi": round, "round": round,
    "min": min, "max": max,
    "moyenne": _moyenne, "mean": _moyenne,
    "mediane": _mediane, "median": _mediane,
    "ecarttype": _ecart_type, "std": _ecart_type,
    "variance": _variance,
}


def _evaluer(noeud):
    if isinstance(noeud, ast.Expression):
        return _evaluer(noeud.body)
    if isinstance(noeud, ast.Constant):
        if isinstance(noeud.value, (int, float)) and \
                not isinstance(noeud.value, bool):
            if abs(noeud.value) > _LIMITES["base_max"]:
                raise ErreurCalcul("Nombre trop grand.")
            return noeud.value
        raise ErreurCalcul("Valeur non autorisee.")
    if isinstance(noeud, ast.BinOp):
        op = _OPS_BIN.get(type(noeud.op))
        if op is None:
            raise ErreurCalcul("Operation non autorisee.")
        gauche, droite = _evaluer(noeud.left), _evaluer(noeud.right)
        if isinstance(noeud.op, ast.Pow):
            if abs(droite) > _LIMITES["exposant_max"] or \
                    abs(gauche) > _LIMITES["base_max"]:
                raise ErreurCalcul("Puissance trop grande.")
        try:
            return op(gauche, droite)
        except ZeroDivisionError:
            raise ZeroDivisionError()
        except OverflowError:
            raise ErreurCalcul("Resultat trop grand.")
    if isinstance(noeud, ast.UnaryOp):
        op = _OPS_UNA.get(type(noeud.op))
        if op is None:
            raise ErreurCalcul("Operation non autorisee.")
        return op(_evaluer(noeud.operand))
    if isinstance(noeud, ast.Name):
        if noeud.id in _CONSTANTES:
            return _CONSTANTES[noeud.id]
        raise ErreurCalcul(f"Symbole inconnu : {noeud.id}")
    if isinstance(noeud, (ast.Tuple, ast.List)):
        return [_evaluer(e) for e in noeud.elts]
    if isinstance(noeud, ast.Call):
        if not isinstance(noeud.func, ast.Name) or \
                noeud.func.id not in _FONCTIONS or noeud.keywords:
            raise ErreurCalcul("Fonction non autorisee.")
        args = [_evaluer(a) for a in noeud.args]
        if len(args) == 1 and isinstance(args[0], list):
            return _FONCTIONS[noeud.func.id](args[0])
        if len(args) == 1 and noeud.func.id in ("sqrt", "racine",
                                                "racinecarree", "abs"):
            if args[0] < 0:
                raise ErreurCalcul("Racine d'un nombre negatif impossible.")
            if abs(args[0]) > _LIMITES["base_max"]:
                raise ErreurCalcul("Nombre trop grand.")
            return _FONCTIONS[noeud.func.id](args[0])
        if noeud.func.id in ("arrondi", "round"):
            if len(args) == 1:
                return round(args[0])
            if len(args) == 2:
                return round(args[0], int(args[1]))
            raise ErreurCalcul("Attendu : 1 ou 2 nombres pour arrondi.")
        if len(args) == 1 and noeud.func.id in _FONCTIONS:
            return _FONCTIONS[noeud.func.id]([args[0]])
        return _FONCTIONS[noeud.func.id](*args)
    raise ErreurCalcul("Expression non autorisee.")


# --- passage du francais vers une expression --------------------------

_PCT = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:%|pour\s?cents?)\s*(?:de|du|des|sur)\s*")
_RACINE = re.compile(r"racines?\s*(?:carrees?\s*)?de\s*")
_LISTE_NOMBRES = re.compile(
    r"\b(moyenne|mediane|ecarts?\s?types?|variance)\b\s*(?:de|des)?\s*"
    r"((?:\d+(?:[.,]\d+)?\s*[,\s]\s*)+\d+(?:[.,]\d+)?)")
_MOTS_VERS_OP = [
    (re.compile(r"\bpuissance\b"), "**"),
    (re.compile(r"\bau\s+carre\b"), "**2"),
    (re.compile(r"\bau\s+cube\b"), "**3"),
    (re.compile(r"\bmultiplic(?:he|ie)s?\s+par\b|\bfois\b"), "*"),
    (re.compile(r"\bdivis(?:he|e)s?\s+par\b"), "/"),
    (re.compile(r"\bplus\b|\bet\s+demi\b"), "+"),
    (re.compile(r"\bmoins\b"), "-"),
]
_MOTS_SUPPRIMES = re.compile(
    r"\b(calculez?|calculs?|combien\s+(?:font|fait|ca\s+fait)?|"
    r"resultats?\s+de|combien\s+vaut|egal)\b")


def _vers_expression(texte):
    t = re.sub(r"\s+", " ", texte.strip().lower())
    # Listes statistiques TRAITEES EN PREMIER : leurs espaces ne doivent
    # pas etre confondus avec des separateurs de milliers (« moyenne de
    # 12 14 16 » -> moyenne([12,14,16])).
    t = _LISTE_NOMBRES.sub(
        lambda m: m.group(1).replace(" ", "") + "([" +
        re.sub(r"[,\s]+", "\x01", m.group(2).strip()) + "])", t)
    t = t.replace(",", ".")           # decimales francaises
    t = re.sub(r"(?<=\d)[ '](?=\d)", "", t)   # separateur de milliers
    t = _PCT.sub(r"(\1/100)*", t)
    t = _RACINE.sub("sqrt(", t)
    # fermer la parenthese du sqrt ouvert ci-dessus si besoin
    if "sqrt(" in t and t.count("(") > t.count(")"):
        t += ")" * (t.count("(") - t.count(")"))
    for motif, remplacement in _MOTS_VERS_OP:
        t = motif.sub(remplacement, t)
    t = _MOTS_SUPPRIMES.sub(" ", t)
    t = t.replace("^", "**").replace("×", "*").replace("÷", "/")
    t = t.replace("x", "*") if re.fullmatch(
        r"[\d\s+\-*/().x]+", t or "") else t
    return re.sub(r"\s+", "", t).replace("\x01", ",")


_NOMS_TRIES = sorted(_FONCTIONS, key=len, reverse=True)
_JETON_VALIDE = re.compile(
    r"(?:\d+(?:\.\d+)?|"
    + "|".join(map(re.escape, _NOMS_TRIES))
    + r"|pi|[+\-*/%()\[\],]|e)+")


def calculer(texte_brut):
    """Point d'entree. Renvoie un dict :
    {"expression", "valeur", "division_par_zero"} ou None si le texte
    n'a pas la forme d'un calcul."""
    texte = (texte_brut or "").strip()
    if not texte or len(texte) > 200:
        return None
    if not re.search(r"\d", texte):
        return None

    expr = _vers_expression(texte)
    if not expr or len(expr) > _LIMITES["longueur_expr"]:
        return None
    # Validation POSITIVE : l'expression doit se decomposer integralement
    # en jetons connus (nombres, operateurs, noms de fonctions autorises).
    # Aucune soustraction de motifs interdits : ce qui n'est pas reconnu
    # est refuse d'office.
    if not _JETON_VALIDE.fullmatch(expr):
        return None
    if not re.search(r"[+\-*/%]|sqrt|moyenne|mediane|ecarttype|variance"
                     r"|\*\*|\[", expr):
        return None
    if not re.search(r"\d", expr):
        return None

    try:
        arbre = ast.parse(expr, mode="eval")
    except (SyntaxError, ValueError, MemoryError):
        return None
    try:
        valeur = _evaluer(arbre)
    except ZeroDivisionError:
        return {"expression": expr, "valeur": None,
                "division_par_zero": True}
    except ErreurCalcul as exc:
        return {"expression": expr, "erreur": str(exc), "valeur": None}
    except (TypeError, ValueError, OverflowError):
        return None

    if isinstance(valeur, float):
        if valeur.is_integer() and abs(valeur) < 1e15:
            valeur = int(valeur)
        else:
            valeur = round(valeur, 6)
    if isinstance(valeur, int) and abs(valeur) >= 1e15:
        return {"expression": expr, "erreur": "Resultat trop grand.",
                "valeur": None}
    return {"expression": expr, "valeur": valeur,
            "division_par_zero": False}
