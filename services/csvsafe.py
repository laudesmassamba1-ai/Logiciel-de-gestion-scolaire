"""Neutralisation de l'injection de formule dans les exports CSV.

Module sans dependance (ni Qt, ni base, ni repositories) : il est utilise
aussi bien par services/ que par repositories/, donc il ne doit importer
personn'un (sinon cycle d'import avec services.reports -> repositories).
"""


def csv_sur(valeur):
    """Rend une cellule CSV inerte vis-a-vis d'Excel / LibreOffice.

    Une cellule commencant par = + - @ (ou \\t / \\r en tete) est interpretee
    comme une FORMULE a l'ouverture : un nom d'eleve « =cmd|' /C calc'!A1 »
    s'executerait chez l'utilisateur qui ouvre l'export. On prefixe ces
    cellules d'une apostrophe, convention qui affiche le texte tel quel.
    """
    if valeur is None:
        return ""
    texte = str(valeur)
    # « - » est le placeholder de ces exports (valeur absente), pas une
    # donnee : il ne doit pas devenir un texte precedé d'apostrophe.
    if texte in ("", "-"):
        return texte
    if texte[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + texte
    return texte
