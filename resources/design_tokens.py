"""Design tokens — seule source de verite du theme.

Les valeurs hexadécimales vivent ici une seule fois ; les composants de
`ui/widgets/` et les gabarits de page n'utilisent que ces classes. Pour
changer le theme, on modifie UNIQUEMENT ce fichier.

Theme « Liquid Glass clair » : fond aurora (bleu glace -> lavande -> ambre),
cartes en verre (blanc, hairline glacee, coins uniformes), accent moderne
bleu -> violet en degradé signature, or conserve comme marque d'ecole
(secondaire). L'esprit : iOS/macOS Ventura + Notion, lisible au quotidien
pour une gestion scolaire. Rayons : SM 10 (fins), MD 12 (controles),
LG 16 (cartes).
"""


class Colors:
    # --- Accent moderne (degrade signature bleu -> violet) ---
    PRIMARY = "#4F6DF5"
    PRIMARY_HOVER = "#3D59E0"
    PRIMARY_PRESSED = "#3350D0"
    PRIMARY_LIGHT = "#E8EDFE"      # fond de selection clair
    PRIMARY_BG = "#F1F4FF"
    PRIMARY_BORDER = "#CDD9FD"
    ACCENT_VIOLET = "#8B5CF6"      # seconde teinte du degrade signature
    VIOLET_LIGHT = "#F0EBFF"
    GRAD_TOP = "#5B7BF7"           # degrade signature (vert. haut)
    GRAD_BOTTOM = "#7C5CF0"        # degrade signature (vert. bas)

    # --- Bleu (alias historique C_BLUE_*) ---
    BLUE = "#4F6DF5"
    BLUE_HOVER = "#3D59E0"
    BLUE_PRESSED = "#3350D0"
    BLUE_LIGHT = "#E8EDFE"
    BLUE_BORDER = "#CDD9FD"

    # --- Violet (assistante Charo, chips apprentissage) ---
    VIOLET_HOVER = "#7A4DF0"
    VIOLET_PRESSED = "#6A3FE0"
    VIOLET_BORDER = "#DDD2FC"

    # --- Or : marque d'ecole (secondaire, plus jamais accent primaire) ---
    GOLD = "#C8960C"
    GOLD_HOVER = "#B7820A"
    GOLD_PRESSED = "#A67409"
    GOLD_LIGHT = "#F6EED7"
    GOLD_BG = "#FBF7EC"
    GOLD_BORDER = "#E9DFC4"
    GOLD_GRAD_TOP = "#E0A81E"
    GOLD_GRAD_BOTTOM = "#B8860B"

    # --- Semantiques ---
    SUCCESS = "#12A45B"
    SUCCESS_DARK = "#0E8A4C"
    SUCCESS_BG = "#E7F8EF"
    SUCCESS_BORDER = "#CDEDDA"

    DANGER = "#E5484D"
    DANGER_HOVER = "#D7353A"
    DANGER_PRESSED = "#C2282E"
    DANGER_BG = "#FFECEE"
    DANGER_BORDER = "#F8D3D6"

    WARNING = "#D9822B"
    WARNING_HOVER = "#C26F1E"
    WARNING_PRESSED = "#A85E16"
    WARNING_BG = "#FFF4E5"
    WARNING_TEXT = "#A9621A"

    INFO = "#4F6DF5"
    INFO_BG = "#EDF2FF"
    INFO_BORDER = "#CDD9FD"

    # --- Textes ---
    TEXT_PRIMARY = "#1E2430"
    TEXT_SECONDARY = "#465064"
    TEXT_MUTED = "#667086"
    TEXT_LIGHT = "#8C96AB"
    EMPTY_STATE = "#59647A"

    # --- Verre / cartes ---
    BORDER = "#E2E9F5"
    BORDER_STRONG = "#C3CFE2"
    CONTOUR = "#4A5568"          # contour net des sections (boutons, cartes, tables)
    FOCUS_RING = "#4F6DF5"

    BG_PAGE = "#F3F6FC"            # secours neutre (fond aurora dans QSS)
    BG_SOFT = "#F0F4FC"
    BG_CARD = "#FFFFFF"
    BG_INPUT = "#FFFFFF"
    GRID = "#DDE5F2"               # lignes de grille (tableaux)

    INK = "#1E2430"
    SIDEBAR_TEXT = "#465064"
    SIDEBAR_MUTED = "#8C96AB"
    SIDEBAR_HOVER = "#EDF2FB"
    SIDEBAR_ACTIVE_BG = "#E7ECFE"
    SIDEBAR_ACTIVE_TEXT = "#3A52D8"

    SHADOW = "36, 52, 100"         # ombre douce bluee (rgba)



class Spacing:
    XS = 6
    SM = 10
    MD = 18
    LG = 28
    XL = 36


class Radius:
    """Rayons d'arrondi — langage commun a toute l'appli.

    SM : controles fins (items de liste, menus, chips)
    MD : boutons, champs de saisie, pastilles
    LG : cartes, etats vides, fenetres
    """
    SM = 10
    MD = 12
    LG = 16


class FontSize:
    CAPTION = 11
    BODY = 13
    SUBTITLE = 14
    TITLE = 18
    PAGE_TITLE = 26
    DISPLAY = 26          # grands chiffres / valeurs KPI


class FontFamily:
    """Familles proposees — `Inter Display` (titres/chiffres) puis `Inter`
    (corps), avec repli systeme. Definies aussi dans `core.config`."""
    DISPLAY = "Inter Display"
    BODY = "Inter"
    # Repli emoji : les polices standard n'ont aucun glyphe picto ; Noto Color
    # Emoji (present sur le systeme) doit figurer dans les listes font-family.
    EMOJI = "Noto Color Emoji"


# ===========================================================================
# Theme personnalise — `data/theme_config.json`
# ---------------------------------------------------------------------------
# Le configurateur graphique (ui/pages/configurateur.py, raccourci cache
# Ctrl+Shift+T) ecrit ce fichier. Il est relu A L'IMPORT de ce module : les
# classes ci-dessus sont donc « sources jumelles » de core.config — les
# memes cles C_* sont surchargees dans ce module ET dans core.config avant
# la construction de tout style (STYLE_*, APP_STYLESHEET).
# ===========================================================================

import json as _json
import os as _os
import sys as _sys
from pathlib import Path as _Path


def _dossier_donnees() -> "_Path":
    """Emplacement des donnees utilisateur (meme regle que core.config.data_dir).

    En exécutable PyInstaller, `__file__` pointe vers le bundle _MEIPASS en
    lecture seule : le theme personnalise doit etre lu/ecrit dans le dossier
    de donnees. Module jumeau de core.config (import croise impossible).
    """
    override = _os.environ.get("GS_DATA_DIR")
    if override:
        return _Path(override) / "data"
    if hasattr(_sys, "_MEIPASS"):
        if _sys.platform == "win32":
            base = _Path(_os.environ.get("APPDATA", str(_Path.home()))) / "GestionScolaire"
        elif _sys.platform == "darwin":
            base = _Path.home() / "Library" / "Application Support" / "GestionScolaire"
        else:
            base = _Path(_os.environ.get("XDG_DATA_HOME", str(_Path.home() / ".local" / "share"))) / "gestion-scolaire"
        return base / "data"
    return _Path(__file__).resolve().parent.parent / "data"


_CHEMIN_THEME = _dossier_donnees() / "theme_config.json"

_THEME = {}
try:
    if _CHEMIN_THEME.exists():
        _THEME = _json.loads(_CHEMIN_THEME.read_text(encoding="utf-8"))
except Exception:
    _THEME = {}

# Mapping cle JSON "couleurs.C_*" -> (classe, attribut)
_MAP_COULEURS = {
    "C_PRIMARY": (Colors, "PRIMARY"),
    "C_PRIMARY_HOVER": (Colors, "PRIMARY_HOVER"),
    "C_PRIMARY_PRESSED": (Colors, "PRIMARY_PRESSED"),
    "C_PRIMARY_LIGHT": (Colors, "PRIMARY_LIGHT"),
    "C_PRIMARY_BG": (Colors, "PRIMARY_BG"),
    "C_PRIMARY_BORDER": (Colors, "PRIMARY_BORDER"),
    "C_BLUE": (Colors, "BLUE"),
    "C_BLUE_HOVER": (Colors, "BLUE_HOVER"),
    "C_BLUE_PRESSED": (Colors, "BLUE_PRESSED"),
    "C_BLUE_LIGHT": (Colors, "BLUE_LIGHT"),
    "C_BLUE_BORDER": (Colors, "BLUE_BORDER"),
    "C_ACCENT_VIOLET": (Colors, "ACCENT_VIOLET"),
    "C_VIOLET_HOVER": (Colors, "VIOLET_HOVER"),
    "C_VIOLET_PRESSED": (Colors, "VIOLET_PRESSED"),
    "C_VIOLET_LIGHT": (Colors, "VIOLET_LIGHT"),
    "C_VIOLET_BORDER": (Colors, "VIOLET_BORDER"),
    "C_GRAD_TOP": (Colors, "GRAD_TOP"),
    "C_GRAD_BOTTOM": (Colors, "GRAD_BOTTOM"),
    "C_GOLD": (Colors, "GOLD"),
    "C_GOLD_HOVER": (Colors, "GOLD_HOVER"),
    "C_GOLD_PRESSED": (Colors, "GOLD_PRESSED"),
    "C_GOLD_LIGHT": (Colors, "GOLD_LIGHT"),
    "C_GOLD_BG": (Colors, "GOLD_BG"),
    "C_GOLD_BORDER": (Colors, "GOLD_BORDER"),
    "C_GOLD_GRAD_TOP": (Colors, "GOLD_GRAD_TOP"),
    "C_GOLD_GRAD_BOTTOM": (Colors, "GOLD_GRAD_BOTTOM"),
    "C_RED": (Colors, "DANGER"),
    "C_RED_HOVER": (Colors, "DANGER_HOVER"),
    "C_RED_PRESSED": (Colors, "DANGER_PRESSED"),
    "C_RED_BG": (Colors, "DANGER_BG"),
    "C_RED_BORDER": (Colors, "DANGER_BORDER"),
    "C_GREEN": (Colors, "SUCCESS"),
    "C_GREEN_DARK": (Colors, "SUCCESS_DARK"),
    "C_GREEN_BG": (Colors, "SUCCESS_BG"),
    "C_GREEN_BORDER": (Colors, "SUCCESS_BORDER"),
    "C_WARNING": (Colors, "WARNING"),
    "C_WARNING_BG": (Colors, "WARNING_BG"),
    "C_WARNING_HOVER": (Colors, "WARNING_HOVER"),
    "C_WARNING_PRESSED": (Colors, "WARNING_PRESSED"),
    "C_WARNING_TEXT": (Colors, "WARNING_TEXT"),
    "C_INFO": (Colors, "INFO"),
    "C_INFO_BG": (Colors, "INFO_BG"),
    "C_INFO_BORDER": (Colors, "INFO_BORDER"),
    "C_TEXT": (Colors, "TEXT_PRIMARY"),
    "C_TEXT_SECONDARY": (Colors, "TEXT_SECONDARY"),
    "C_TEXT_MUTED": (Colors, "TEXT_MUTED"),
    "C_TEXT_LIGHT": (Colors, "TEXT_LIGHT"),
    "C_EMPTY_STATE": (Colors, "EMPTY_STATE"),
    "C_BG": (Colors, "BG_PAGE"),
    "C_BG_ALT": (Colors, "BG_INPUT"),
    "C_BG_SOFT": (Colors, "BG_SOFT"),
    "C_CARD": (Colors, "BG_CARD"),
    "C_BORDER": (Colors, "BORDER"),
    "C_BORDER_STRONG": (Colors, "BORDER_STRONG"),
    "C_CONTOUR": (Colors, "CONTOUR"),
    "C_FOCUS_RING": (Colors, "FOCUS_RING"),
    "C_GRID": (Colors, "GRID"),
    "C_INK": (Colors, "INK"),
    "C_SIDEBAR_TEXT": (Colors, "SIDEBAR_TEXT"),
    "C_SIDEBAR_MUTED": (Colors, "SIDEBAR_MUTED"),
    "C_SIDEBAR_HOVER": (Colors, "SIDEBAR_HOVER"),
    "C_SIDEBAR_ACTIVE": (Colors, "SIDEBAR_ACTIVE_BG"),
    "C_SIDEBAR_ACTIVE_TEXT": (Colors, "SIDEBAR_ACTIVE_TEXT"),
    "C_SHADOW": (Colors, "SHADOW"),
}

_COULEURS = _THEME.get("couleurs", {}) if isinstance(_THEME, dict) else {}
for _cle, (_cls, _attr) in _MAP_COULEURS.items():
    _val = _COULEURS.get(_cle)
    if isinstance(_val, str) and _val:
        setattr(_cls, _attr, _val)

# Dimensionnements : tailles de police, rayons, espacements.
_MAP_NUMERIQUES = {
    "taille_titre_page": (FontSize, "PAGE_TITLE"),
    "taille_chiffres_kpi": (FontSize, "DISPLAY"),
    "taille_sous_titre": (FontSize, "SUBTITLE"),
    "taille_corps": (FontSize, "BODY"),
    "taille_caption": (FontSize, "CAPTION"),
    "rayon_sm": (Radius, "SM"),
    "rayon_md": (Radius, "MD"),
    "rayon_lg": (Radius, "LG"),
    "rayon_carte": (Radius, "LG"),   # meme rayon que les cartes STYLE_CARD
    "espace_xs": (Spacing, "XS"),
    "espace_sm": (Spacing, "SM"),
    "espace_md": (Spacing, "MD"),
    "espace_lg": (Spacing, "LG"),
}
_DIMS = _THEME.get("dimensions", {}) if isinstance(_THEME, dict) else {}
for _cle, (_cls, _attr) in _MAP_NUMERIQUES.items():
    _val = _DIMS.get(_cle)
    if isinstance(_val, (int, float)) and _val > 0:
        setattr(_cls, _attr, int(_val))

# Polices (corps / titres-display).
_TYPO = _THEME.get("typo", {}) if isinstance(_THEME, dict) else {}
if isinstance(_TYPO.get("police_corps"), str) and _TYPO["police_corps"]:
    FontFamily.BODY = _TYPO["police_corps"]
if isinstance(_TYPO.get("police_titres"), str) and _TYPO["police_titres"]:
    FontFamily.DISPLAY = _TYPO["police_titres"]

# Cache du theme brut pour le configurateur graphique.
THEME_BRUT = _THEME