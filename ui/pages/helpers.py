import datetime
from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTableWidgetItem, QVBoxLayout, QTableWidget, QHeaderView,
)

from core.config import (
    C_PRIMARY, C_TEXT_SECONDARY, C_TEXT_MUTED, C_BORDER, C_BG_ALT, C_EMPTY_STATE,
    STYLE_BTN_PRIMARY, STYLE_TABLE, STYLE_HEADER_TITLE, STYLE_HEADER_SUBTITLE,
    STYLE_EMPTY_STATE, STYLE_STATUS, STYLE_CARD, STYLE_SELECTOR,
)
from repositories import repos


class PageContext:
    def __init__(self, user, navigate):
        self.user = user
        self.role = user["role"]
        from core.config import ROLE_LABELS
        from services.auth import RoleAuthorizer
        self.role_label = ROLE_LABELS.get(self.role, self.role)
        self.authorizer = RoleAuthorizer(self.role)
        self.navigate = navigate

    def can_edit(self, page):
        return self.authorizer.can_edit(page)


def _btn(text, callback, style=None, max_h=None):
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    if max_h:
        b.setMaximumHeight(max_h)
    if style:
        b.setStyleSheet(style)
    b.clicked.connect(callback)
    return b


def _simple_btn_style(bg=None, fg=None, border=None):
    bg = bg or C_BG_ALT
    fg = fg or C_TEXT_SECONDARY
    border = border or C_BORDER
    return (f"background-color: {bg}; color: {fg}; border: 1px solid {border};"
            " border-radius: 8px; padding: 6px 12px; font-size: 12px; font-weight: 600;")


def _money_edit(value=0, minimum=0, maximum=100000000):
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setDecimals(0)
    spin.setValue(value)
    spin.setPrefix("")
    spin.setSuffix(" FCFA")
    return spin


def _today_fr():
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre"]
    d = datetime.date.today()
    return f"{jours[d.weekday()]} {d.day} {mois[d.month - 1]} {d.year}"


def _fill_combos(combo, items, clear_first=True):
    if clear_first:
        combo.clear()
    for item in items:
        combo.addItem(item)


def _reload_combo(combo, items, selected_id=None):
    if selected_id is None:
        selected_id = combo.currentData()
    combo.blockSignals(True)
    combo.clear()
    for label, data in items:
        combo.addItem(label, data)
    idx = combo.findData(selected_id)
    if idx >= 0:
        combo.setCurrentIndex(idx)
    elif combo.count():
        combo.setCurrentIndex(0)
    combo.blockSignals(False)


def _classe_items(avec_toutes=True):
    items = [(c["nom"], c["id"]) for c in repos.classes()]
    if avec_toutes:
        items.insert(0, ("Toutes les classes", None))
    return items


def _fit_rows(t):
    t.verticalHeader().setDefaultSectionSize(40)


def _make_table(headers):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectRows)
    t.setAlternatingRowColors(True)
    t.setShowGrid(False)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(42)
    t.horizontalHeader().setStretchLastSection(True)
    t.horizontalHeader().setMinimumSectionSize(80)
    t.setStyleSheet(STYLE_TABLE)
    t.horizontalHeader().setHighlightSections(False)
    return t


def _page_header(parent_lay, titre, sous_titre):
    header = QVBoxLayout()
    header.setSpacing(4)
    t = QLabel(titre)
    t.setStyleSheet(STYLE_HEADER_TITLE)
    s = QLabel(sous_titre)
    s.setStyleSheet(STYLE_HEADER_SUBTITLE)
    header.addWidget(t)
    header.addWidget(s)

    accent = QFrame()
    accent.setFixedSize(46, 3)
    accent.setStyleSheet(
        f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
        f" stop:0 #DAA520, stop:1 rgba(218,165,32,0));"
        " border: none; border-radius: 2px; margin-top: 2px;")
    header.addWidget(accent)
    parent_lay.addLayout(header)


def _kpi_card(label, valeur, couleur=C_PRIMARY):
    frame = QFrame()
    frame.setStyleSheet(
        f"background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
        f" stop:0 #FFFFFF, stop:1 #FAF9F6); border: 1px solid #E6E3DB;"
        f" border-radius: 14px; border-top: 3px solid {couleur};")
    v = QVBoxLayout(frame)
    v.setContentsMargins(16, 14, 16, 14)
    v.setSpacing(2)
    val = QLabel(str(valeur))
    val.setObjectName("kpi_value")
    val.setStyleSheet(f"font-size: 23px; font-weight: 800; color: {couleur};")
    lab = QLabel(label)
    lab.setStyleSheet(f"font-size: 11px; color: {C_TEXT_MUTED}; font-weight: 500;")
    v.addWidget(val)
    v.addWidget(lab)
    return frame


def _styler_carte(frame, accent=None):
    """Style moderne d'une carte existante (bande d'accent or en haut).

    Utilisee par les tableaux de bord dont les frames viennent des .ui.
    """
    if accent is None:
        accent = C_PRIMARY
    try:
        frame.setStyleSheet(
            f"QFrame {{ background-color: qlineargradient(x1:0, y1:0,"
            f" x2:0, y2:1, stop:0 #FFFFFF, stop:1 #FAF9F6);"
            f" border: 1px solid #E6E3DB; border-radius: 14px;"
            f" border-top: 3px solid {accent}; }}")
    except RuntimeError:
        pass


def _add_btn(text, callback):
    return _btn(text, callback, STYLE_BTN_PRIMARY)


def _replace_layout(layout, widget):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()
    layout.addWidget(widget)


def _appreciation(moyenne):
    from services.appreciations import appreciation
    return appreciation(moyenne)


def _parse_money(text):
    """Convertit une saisie monetaire en float ; renvoie 0.0 si aucune
    valeur numerique exploitable (champ vide, "FCFA", texte libre...)."""
    if text is None:
        return 0.0
    nettoye = str(text).replace(" ", "").replace(",", "").replace("FCFA", "").strip()
    if not nettoye:
        return 0.0
    try:
        return float(nettoye)
    except ValueError:
        return 0.0


def date_dans_annee_active(date_iso):
    """Logique pure : True si la date ISO tombe dans l'annee scolaire active.

    Pas d'annee definie -> garde desactivee (l'alerte de configuration est
    affichee par refuser_si_hors_annee).
    """
    a = repos.annee_scolaire_active()
    if not a or not a.get("date_debut"):
        return True
    debut = str(a["date_debut"])
    fin = str(a.get("date_fin") or "9999-12-31")
    return bool(date_iso) and debut <= date_iso <= fin


def refuser_si_hors_annee(parent, date_iso, label="La date"):
    """Garde de coherence : aucune ecriture datee hors annee scolaire active.

    Affiche l'explication a l'utilisateur et renvoie True si la saisie
    doit etre refusee.
    """
    a = repos.annee_scolaire_active()
    if not a or not a.get("date_debut"):
        QMessageBox.warning(
            parent, "Annee scolaire",
            "Aucune annee scolaire active n'est definie.\n\n"
            "Ouvrez 'Cycles & Annees Scolaires' pour creer/activer "
            "l'annee en cours avant toute saisie.")
        return True
    if not date_dans_annee_active(date_iso):
        QMessageBox.warning(
            parent, "Date hors annee scolaire",
            f"{label} ({date_iso}) est en dehors de l'annee scolaire active :\n"
            f"{a['libelle']}  ({a['date_debut']} → {a.get('date_fin') or '?'})\n\n"
            "Choisissez une date dans l'annee active, ou changez d'annee "
            "active dans 'Cycles & Annees Scolaires'.")
        return True
    return False
