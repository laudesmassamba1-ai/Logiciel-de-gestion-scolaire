import datetime
from functools import partial

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QTableWidgetItem, QVBoxLayout,
    QTableWidget, QHeaderView, QWidget, QSizePolicy,
)

from core.config import (
    C_PRIMARY, C_ACCENT_VIOLET, C_TEXT, C_TEXT_SECONDARY, C_TEXT_MUTED,
    C_TEXT_LIGHT, C_BORDER, C_BG_ALT, C_EMPTY_STATE, C_BORDER_STRONG, C_RED,
    C_RED_BG, C_CARD, C_BG_SOFT, C_BLUE_BORDER, C_BLUE_LIGHT, C_GOLD, C_GOLD_BORDER,
    C_GOLD_LIGHT, C_GOLD_BG, C_GOLD_PRESSED, C_CONTOUR, APP_FONT_FAMILY, FONT_DISPLAY_FAMILY,
    FONT_EMOJI,
    STYLE_BTN_PRIMARY, STYLE_TABLE, STYLE_HEADER_TITLE,
    STYLE_EMPTY_STATE, STYLE_STATUS, STYLE_CARD, STYLE_SELECTOR,
)
from repositories import repos


def _ombre_cartoon(widget, dy=4, alpha=0.16, blur=0):
    """Ombre portee NETTE (« cartoon » mais pro) : nette par defaut (blur 0),
    decalee de `dy` px vers le bas, couleur bleue invisible a 10-16 %.
    A utiliser sur les cartes, KPI, tableaux, etats vides - jamais sur des
    labels ou widgets de controle (surcout de rendu, effet sale)."""
    ombre = QGraphicsDropShadowEffect(widget)
    ombre.setBlurRadius(blur)
    ombre.setOffset(0, dy)
    ombre.setColor(QColor(31, 45, 80, int(255 * alpha)))
    widget.setGraphicsEffect(ombre)
    return ombre


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
    if text.startswith("+"):
        _poser_icone_plus(b, style)
    b.clicked.connect(callback)
    return b


def _poser_icone_plus(btn, style=None):
    """Icone '+' gauche sur les boutons d'ajout (qtawesome, optionnel)."""
    try:
        import qtawesome as qta
    except ImportError:
        return
    style = style or ""
    if (C_BLUE_LIGHT in style or C_BLUE_BORDER in style or C_PRIMARY in style):
        couleur = C_PRIMARY
    elif C_GOLD in style or C_GOLD_BORDER in style or C_GOLD_LIGHT in style \
            or C_GOLD_BG in style:
        couleur = C_GOLD_PRESSED
    elif C_RED_BG in style:
        couleur = C_RED
    elif C_CARD in style:
        couleur = C_CARD
    else:
        couleur = C_TEXT_LIGHT
    try:
        btn.setIcon(qta.icon("fa5s.plus", color=couleur))
        btn.setIconSize(QSize(15, 15))
    except Exception:
        pass


def _simple_btn_style(bg=None, fg=None, border=None, compact=False):
    bg = bg or C_BG_ALT
    fg = fg or C_TEXT_SECONDARY
    border = border or C_CONTOUR
    if compact:
        # Boutons de cellule : padding reduit pour ne jamais etre tronques
        # dans une colonne d'actions (le texte doit tenir sans depasser).
        return (f"background-color: {bg}; color: {fg}; border: 1px solid {border};"
                " border-radius: 10px; padding: 5px 10px;"
                " font-size: 12px; font-weight: 600;")
    return (f"background-color: {bg}; color: {fg}; border: 1px solid {border};"
            " border-radius: 12px; padding: 8px 16px; font-size: 13px; font-weight: 600;")


def _fond_aurora_dialog(dlg):
    """Remplace le fond blanc des .ui live par l'aurora du theme.

    Le QSS des .ui pose `QDialog { background-color: #FFFFFF; }` qui
    prime sur APP_STYLESHEET : on repond sur le QSS charge pour remplacer
    UNIQUEMENT cette regle (les cartes et champs restent blancs).
    """
    from core.config import C_AURORA
    qss = dlg.styleSheet() or ""
    ancien = "QDialog { background-color: #FFFFFF; }"
    if ancien in qss:
        nouveau = f"QDialog {{ background: {C_AURORA} }}"
        dlg.setStyleSheet(qss.replace(ancien, nouveau))


def _adapter_hauteur(dlg):
    """Ajuste la hauteur d'un dialogue au contenu reel, sans jamais
    depasser l'ecran disponible (evite contenu rogne ou boutons hors champ)."""
    from PyQt5.QtWidgets import QApplication
    lay = dlg.layout()
    if lay is None:
        return
    besoin = max(lay.sizeHint().height(), lay.minimumSize().height())
    dispo = QApplication.primaryScreen().availableGeometry().height() - 64
    hauteur = min(besoin, max(dispo, 420))
    dlg.setMinimumHeight(hauteur)
    dlg.resize(dlg.width(), hauteur)


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
    t.verticalHeader().setDefaultSectionSize(44)


def _fill_table_space(t):
    """Repartit la largeur disponible sur toute la table, sans couper.

    Les colonnes gardent la taille suffisante pour leur contenu (aucun
    texte tronque) puis la place restante est distribuee de maniere egale.
    Sur un ecran large, la table ne laisse plus un gros vide a droite.
    """
    header = t.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Interactive)
    t.resizeColumnsToContents()
    count = header.count()
    if count == 0:
        return
    disponible = header.width()
    utilise = sum(header.sectionSize(i) for i in range(count))
    if utilise >= disponible:
        return
    extra = (disponible - utilise) // count
    for i in range(count):
        header.resizeSection(i, header.sectionSize(i) + extra)
    header.setSectionResizeMode(QHeaderView.Interactive)


def _actions_cell(*btns):
    """Cellule d'actions alignees a droite (ideale en derniere colonne).

    Les boutons restent proches du bord droit au lieu de flotter sur un
    gros espace vide au milieu de la ligne.
    """
    cell = QWidget()
    lay = QHBoxLayout(cell)
    lay.setContentsMargins(4, 2, 6, 2)
    lay.setSpacing(6)
    lay.addStretch(1)
    for b in btns:
        lay.addWidget(b)
    return cell


def _make_table(headers):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectRows)
    t.setAlternatingRowColors(True)
    t.setShowGrid(False)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True)
    t.horizontalHeader().setMinimumSectionSize(80)
    t.setStyleSheet(STYLE_TABLE)
    t.horizontalHeader().setHighlightSections(False)
    return t


def _page_header(parent_lay, titre):
    header = QVBoxLayout()
    header.setSpacing(4)
    t = QLabel(titre)
    t.setStyleSheet(
        f"font-size: 24px; font-weight: 700; color: {C_TEXT}; margin: 0;")
    header.addWidget(t)

    accent = QFrame()
    accent.setFixedSize(46, 3)
    accent.setStyleSheet(
        f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
        f" stop:0 {C_PRIMARY}, stop:1 {C_ACCENT_VIOLET});"
        " border: none; border-radius: 2px; margin-top: 2px;")
    header.addWidget(accent)
    parent_lay.addLayout(header)


def _kpi_card(label, valeur, couleur=C_PRIMARY):
    frame = QFrame()
    frame.setMaximumHeight(92)
    frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    frame.setStyleSheet(
        f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
        f" stop:0 {C_CARD}, stop:1 {C_BG_SOFT});"
        f" border: 1px solid {C_BORDER};"
        f" border-radius: 16px;")
    v = QVBoxLayout(frame)
    v.setContentsMargins(16, 10, 16, 10)
    v.setSpacing(4)
    val = QLabel(str(valeur))
    val.setObjectName("kpi_value")
    val.setStyleSheet(
        f"font-family: '{FONT_DISPLAY_FAMILY}', '{APP_FONT_FAMILY}', '{FONT_EMOJI}', 'Segoe UI', sans-serif;"
        f" font-size: 26px; font-weight: 800; letter-spacing: -0.5px;"
        f" color: {couleur}; border: none; background: transparent;")
    lab = QLabel(label)
    lab.setStyleSheet(
        "font-size: 10px; text-transform: uppercase; letter-spacing: 1.2px;"
        f" font-weight: 700; color: {C_TEXT_MUTED}; border: none; background: transparent;")
    v.addWidget(val)
    v.addWidget(lab)
    _ombre_cartoon(frame, dy=4, alpha=0.14)
    return frame


def _styler_carte(frame, accent=None):
    """Style « Apple minimal » d'une carte existante : fond blanc, coins
    uniformes, hairline 1 px. `accent` est conserve pour compatibilite de
    signature mais n'est plus dessine (aucune bande).

    Utilisee par les tableaux de bord dont les frames viennent des .ui.
    Le selecteur est porte par l'objectName de la frame : une regle
    "QFrame { ... }" nue cascade sur les QLabel enfants (ils deviennent
    eux aussi des cadres), seule une regle "QFrame#nom" est ciblee.
    """
    try:
        nom = frame.objectName() or "carteStylee"
        frame.setObjectName(nom)
        frame.setStyleSheet(
            f"QFrame#{nom} {{ background-color: {C_CARD};"
            f" border: 1px solid {C_BORDER};"
            f" border-radius: 16px; }}")
        _ombre_cartoon(frame, dy=4, alpha=0.14)
    except RuntimeError:
        pass


def _borner_carte_kpi(frame, hauteur=94):
    """Borne la hauteur d'une carte KPI (chiffre + libelle) chargee depuis
    un .ui, pour qu'elle ne s'etire jamais verticalement."""
    if frame is None:
        return
    try:
        frame.setMaximumHeight(hauteur)
        frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
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
        else:
            sub = item.layout()
            if sub:
                _replace_layout(sub, None)
    if widget is not None:
        layout.addWidget(widget)


def _appreciation(moyenne):
    from services.appreciations import appreciation
    return appreciation(moyenne)


def _empty_state(texte, sous_titre="", bouton=None, hauteur=180):
    """Etat vide compact : message centre (et optionnellement un bouton
    d'action), jamais un grand cadre vide.

    `bouton` est un QPushButton deja construit (facon _add_btn/_btn).
    """
    box = QFrame()
    box.setMaximumHeight(hauteur)
    box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    box.setStyleSheet(
        f"QFrame {{ background: {C_CARD};"
        f" border: 1px dashed {C_BORDER_STRONG}; border-radius: 12px; }}")
    lay = QVBoxLayout(box)
    lay.setContentsMargins(20, 16, 20, 16)
    lay.setSpacing(6)
    msg = QLabel(texte)
    msg.setStyleSheet(
        f"color: {C_EMPTY_STATE}; font-size: 14px; font-weight: 600;"
        " border: none; background: transparent;")
    msg.setAlignment(Qt.AlignCenter)
    msg.setWordWrap(True)
    lay.addWidget(msg)
    if sous_titre:
        sub = QLabel(sous_titre)
        sub.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: 12px;"
            " border: none; background: transparent;")
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub)
    if bouton is not None:
        bouton_lay = QHBoxLayout()
        bouton_lay.addStretch(1)
        bouton_lay.addWidget(bouton)
        bouton_lay.addStretch(1)
        lay.addLayout(bouton_lay)
    return box


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


def _boite_confirmer(parent, texte, titre="Confirmation"):
    """Construit (sans exec) la boite « Oui / Non » française.

    Factoree hors de confirmer() pour permettre aux tests d'inspecter la
    structure (boutons, defaut) sans boucle modale, qui peut planter dans
    l'environnement offscreen de la CI Windows."""
    from PyQt5.QtWidgets import QMessageBox as _B

    boite = _B(_B.Question, titre, texte, _B.NoButton, parent)
    oui = boite.addButton("Oui", _B.YesRole)
    non = boite.addButton("Non", _B.NoRole)
    boite.setDefaultButton(non)
    return boite, oui


def confirmer(parent, texte, titre="Confirmation"):
    """Confirmation destructive avec boutons francaise « Oui / Non ».

    Les QMessageBox par defaut affichent des boutons anglais (Yes/No) :
    cette fenetre propose la meme question en francais et le bouton
    par defaut est « Non » (pivot le plus sur des actions destructrices).
    """
    boite, oui = _boite_confirmer(parent, texte, titre)
    boite.exec_()
    return boite.clickedButton() is oui


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
