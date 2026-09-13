"""Design tokens — seule source de verite du theme.

Les valeurs hexadécimales vivent ici une seule fois ; les composants de
`ui/widgets/` et les gabarits de page n'utilisent que ces classes. Pour
changer le theme, on modifie UNIQUEMENT ce fichier.

Palette actuelle : or (#C8960C) sur fond gris-bleu froid (#E7EBF3),
validee avec l'utilisateur (ne PAS revenir au vert du mandat precedent).
"""


class Colors:
    PRIMARY = "#C8960C"
    PRIMARY_HOVER = "#DAA520"
    PRIMARY_PRESSED = "#A67B0A"
    PRIMARY_LIGHT = "#FEF3C7"
    PRIMARY_BG = "#FFFBEB"
    PRIMARY_BORDER = "#FDE68A"

    DANGER = "#B91C1C"
    DANGER_BG = "#FEF2F2"
    DANGER_BORDER = "#FECACA"

    WARNING = "#D97706"

    INFO = "#1E40AF"
    INFO_BG = "#EFF6FF"
    INFO_BORDER = "#BFDBFE"

    SUCCESS = PRIMARY

    TEXT_PRIMARY = "#1D1D1F"
    TEXT_SECONDARY = "#3A3A40"
    TEXT_MUTED = "#6E6E73"
    TEXT_LIGHT = "#8A8A93"
    EMPTY_STATE = "#5B5B64"

    BORDER = "#DAE0EA"
    BORDER_STRONG = "#C4CCDA"
    FOCUS_RING = "#C8960C"

    BG_PAGE = "#E7EBF3"
    BG_SOFT = "#F6F8FB"
    BG_CARD = "#FFFFFF"
    BG_INPUT = "#F8FAFC"

    INK = "#20202A"
    SIDEBAR_TEXT = "#3E4451"
    SIDEBAR_MUTED = "#99A2B2"
    SIDEBAR_HOVER = "#FFFFFF"
    SIDEBAR_ACTIVE_BG = "#FFFAEB"
    SIDEBAR_ACTIVE_TEXT = "#8A6410"

    GRAD_TOP = "#F0BC45"
    GRAD_BOTTOM = "#C28C0C"

    SHADOW = "46, 60, 80"


class Spacing:
    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32


class Radius:
    """Rayons d'arrondi — langage commun a toute l'appli.

    SM : controles fins (items de liste, menus)
    MD : boutons, champs de saisie, pastilles
    LG : cartes, etats vides, fenetres
    """
    SM = 9
    MD = 12
    LG = 16


class FontSize:
    CAPTION = 11
    BODY = 13
    SUBTITLE = 14
    TITLE = 18
    PAGE_TITLE = 24