"""Fenetre dediee aux modeles de documents personnalises.

L'ecole cree ses documents depuis zero dans un editeur de texte enrichi
(type « Word » : gras, italique, souligne, tailles, alignements, listes,
tableaux, images, couleurs, recherche/remplace, undo/redo), y insere des
variables `{{cle}}`, les enregistre comme modeles reutilisables, puis
genere des PDF pour un eleve, une classe ou « l'ecole » — memes bandeaux,
en-tete et signature que les documents officiels. Le PDF genere atterrit
dans l'Espace Documents.

Variables disponibles : ecole (nom, pays, ville, date, annee scolaire,
signataire), eleve (nom, prenom, matricule, sexe, naissance, classe,
statut, inscription), classe (nom, cycle, effectif).
"""

import base64
import json
import re
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QBuffer, QIODevice, Qt, QTimer, QUrl, QSize
from PyQt5.QtGui import (
    QColor, QDesktopServices, QFont, QIcon, QKeySequence,
    QTextBlockFormat, QTextCharFormat, QTextCursor, QTextImageFormat,
    QTextListFormat, QTextTableFormat,
)
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import (
    QAction, QApplication, QCheckBox, QColorDialog, QComboBox,
    QDialog, QDialogButtonBox, QFileDialog, QGraphicsDropShadowEffect,
    QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QPushButton, QShortcut, QSplitter, QTableWidget,
    QTableWidgetItem, QTextEdit, QToolBar, QVBoxLayout, QWidget,
)

from core.config import (
    APP_FONT_FAMILY, C_BG_SOFT, C_BORDER, C_BORDER_STRONG, C_PRIMARY,
    C_PRIMARY_LIGHT, C_PRIMARY_PRESSED, C_RED, C_RED_BG, C_RED_BORDER,
    C_TEXT_SECONDARY, C_TEXT, C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER,
    C_GREEN, C_GREEN_BG, C_CARD, C_BG,
)
from repositories import repos
from services import modeles_documents as modele_svc
from services.pdf_export import _ouvrir_pdf
from ui import toast
from ui.pages.documents_page import _ANNULE, _dialogue_eleve
from ui.pages.helpers import _btn, _simple_btn_style


def _dialogue_classe(parent, titre):
    """Choix d'une classe. Renvoie l'id, ou `_ANNULE` si annule."""
    classes = repos.classes()
    dlg = QDialog(parent)
    dlg.setWindowTitle(titre)
    dlg.setMinimumSize(400, 110)
    lay = QVBoxLayout(dlg)
    combo = QComboBox()
    for c in classes:
        combo.addItem(c["nom"], c["id"])
    lay.addWidget(combo)
    boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    boutons.rejected.connect(dlg.reject)
    boutons.accepted.connect(dlg.accept)
    lay.addWidget(boutons)
    dlg.exec_()
    if dlg.result() == QDialog.Accepted and combo.currentData() is not None:
        return combo.currentData()
    return _ANNULE


class FenetreModeles(QDialog):
    """Editeur des modeles de documents (liste + zone de saisie + generation)."""

    def __init__(self, parent, ctx):
        super().__init__(parent)
        self.setWindowTitle("Modeles de documents personnalises")
        self.resize(980, 620)
        self.setMinimumSize(860, 520)
        self._ctx = ctx
        self._selection = None
        self._modifie = False

        self._construire()
        self._recharger_liste()

# ------------------------------------------------------------------
    def _construire(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        lay.setContentsMargins(8, 8, 8, 8)

        # Splitter principal : liste + editeur
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(6)
        self.splitter.setChildrenCollapsible(False)
        lay.addWidget(self.splitter, 1)

        # ================================================================
        # PANNEAU GAUCHE : Liste des modeles + actions
        # ================================================================
        gauche = QWidget()
        gauche.setMinimumWidth(260)
        gauche.setMaximumWidth(380)
        g_lay = QVBoxLayout(gauche)
        g_lay.setSpacing(8)
        g_lay.setContentsMargins(8, 8, 8, 8)

        # Barre de recherche / filtre
        search_bar = QHBoxLayout()
        self.search_modele = QLineEdit()
        self.search_modele.setPlaceholderText("Rechercher un modele...")
        self.search_modele.setClearButtonEnabled(True)
        self.search_modele.textChanged.connect(self._filtrer_modeles)
        search_bar.addWidget(self.search_modele)
        g_lay.addLayout(search_bar)

        # Onglets : Tous / Mes modeles / Favoris
        from PyQt5.QtWidgets import QTabWidget
        self.tabs_modeles = QTabWidget()
        self.tabs_modeles.setDocumentMode(True)
        self.tabs_modeles.setTabPosition(QTabWidget.North)
        
        # Onglet "Tous"
        self.page_tous = QWidget()
        t_tous = QVBoxLayout(self.page_tous)
        t_tous.setContentsMargins(0, 0, 0, 0)
        self.liste = QListWidget()
        self.liste.setAlternatingRowColors(True)
        self.liste.setStyleSheet(f"""
            QListWidget {{ background: {C_CARD}; border: 1px solid {C_BORDER};
                border-radius: 10px; }}
            QListWidget::item {{ padding: 9px 12px; border-radius: 8px;
                border-bottom: 1px solid #E3EAF6; }}
            QListWidget::item:selected {{ background: {C_PRIMARY_LIGHT}; }}
        """)
        self.liste.currentItemChanged.connect(self._changer_modele)
        self.liste.setContextMenuPolicy(Qt.CustomContextMenu)
        self.liste.customContextMenuRequested.connect(self._menu_contextuel_liste)
        ombre_liste = QGraphicsDropShadowEffect(self.liste)
        ombre_liste.setBlurRadius(0); ombre_liste.setOffset(0, 3)
        ombre_liste.setColor(QColor(31, 45, 80, 30))
        self.liste.setGraphicsEffect(ombre_liste)
        t_tous.addWidget(self.liste)
        self.tabs_modeles.addTab(self.page_tous, "Tous")

        # Onglet "Favoris"
        self.page_favoris = QWidget()
        t_fav = QVBoxLayout(self.page_favoris)
        t_fav.setContentsMargins(0, 0, 0, 0)
        self.liste_favoris = QListWidget()
        self.liste_favoris.setAlternatingRowColors(True)
        self.liste_favoris.setStyleSheet(self.liste.styleSheet())
        self.liste_favoris.currentItemChanged.connect(self._changer_modele_favori)
        self.liste_favoris.setContextMenuPolicy(Qt.CustomContextMenu)
        self.liste_favoris.customContextMenuRequested.connect(self._menu_contextuel_favori)
        t_fav.addWidget(self.liste_favoris)
        self.tabs_modeles.addTab(self.page_favoris, "Favoris \u2605")

        g_lay.addWidget(self.tabs_modeles, 1)

        # Actions sur les modeles
        gest = QHBoxLayout()
        gest.setSpacing(6)
        gest.addWidget(_btn("Nouveau", self._nouveau,
                            _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY,
                                              border=C_BORDER)))
        gest.addWidget(_btn("Dupliquer", self._dupliquer,
                            _simple_btn_style(bg=C_BG_SOFT, fg=C_TEXT_SECONDARY,
                                              border=C_BORDER)))
        g_droite = QVBoxLayout()
        g_droite.setSpacing(6)
        g_droite.addWidget(_btn("Renommer", self._renommer,
                                _simple_btn_style(bg=C_BG_SOFT,
                                                  fg=C_TEXT_SECONDARY,
                                                  border=C_BORDER)))
        g_droite.addWidget(_btn("Supprimer", self._supprimer,
                                _simple_btn_style(bg=C_RED_BG, fg=C_RED,
                                                  border=C_RED_BORDER)))
        gest.addLayout(g_droite)
        g_lay.addLayout(gest)

        # Import / Export
        io_lay = QHBoxLayout()
        io_lay.setSpacing(6)
        io_lay.addWidget(_btn("Importer", self._importer_modele,
                              _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE,
                                                border=C_BLUE_BORDER)))
        io_lay.addWidget(_btn("Exporter", self._exporter_modele,
                              _simple_btn_style(bg=C_GREEN_BG, fg=C_GREEN,
                                                border=C_BORDER)))
        g_lay.addLayout(io_lay)

        self.splitter.addWidget(gauche)

        # ================================================================
        # PANNEAU DROIT : Editeur "type Word"
        # ================================================================
        droite = QWidget()
        d_lay = QVBoxLayout(droite)
        d_lay.setSpacing(6)
        d_lay.setContentsMargins(8, 8, 8, 8)

        # --- Editeur principal (crée AVANT la toolbar pour éviter AttributeError) ---
        self.editeur = QTextEdit()
        self.editeur.setAcceptRichText(True)
        fonte = QFont(APP_FONT_FAMILY, 11)
        self.editeur.setFont(fonte)
        self.editeur.setPlaceholderText("Redigez ici votre document, comme dans Word...")
        self.editeur.setStyleSheet(f"""
            QTextEdit {{ background: {C_CARD}; border: 1px solid {C_BORDER};
                border-radius: 10px; }}
        """)
        ombre_editeur = QGraphicsDropShadowEffect(self.editeur)
        ombre_editeur.setBlurRadius(0); ombre_editeur.setOffset(0, 3)
        ombre_editeur.setColor(QColor(31, 45, 80, 30))
        self.editeur.setGraphicsEffect(ombre_editeur)
        self.editeur.textChanged.connect(self._marquer_modifie)
        self.editeur.currentCharFormatChanged.connect(self._sync_format)
        self.editeur.cursorPositionChanged.connect(self._update_cursor_info)

        # --- Barre d'outils principale (style ruban Word) ---
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(18, 18))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toolbar.setStyleSheet(f"""
            QToolBar {{ background: transparent; border: none; spacing: 2px; }}
            QToolButton {{ padding: 5px 10px; border-radius: 8px; font-size: 12px; }}
            QToolButton:hover {{ background: {C_BG_SOFT}; }}
            QToolButton:pressed {{ background: {C_BORDER_STRONG}; }}
            QToolButton:checked {{ background: {C_PRIMARY_LIGHT}; color: {C_PRIMARY}; font-weight: 600; }}
            QToolButton[popupMode="1"] {{ padding-right: 18px; }}
        """)
        d_lay.addWidget(self.toolbar)

        self._construire_barre_outils()

        # --- Zone d'editeur + apercu en split vertical ---
        self.editor_split = QSplitter(Qt.Vertical)
        self.editor_split.setHandleWidth(4)
        self.editor_split.setChildrenCollapsible(False)
        d_lay.addWidget(self.editor_split, 1)

        self.editor_split.addWidget(self.editeur)

        # Panneau d'aperçu HTML (optionnel, repliable)
        self.apercu_widget = QWidget()
        self.apercu_widget.setVisible(False)
        a_lay = QVBoxLayout(self.apercu_widget)
        a_lay.setContentsMargins(0, 0, 0, 0)
        self.lbl_apercu_titre = QLabel("Aperçu temps réel (HTML)")
        self.lbl_apercu_titre.setStyleSheet(f"color:{C_TEXT_SECONDARY};font-size:12px;font-weight:600;padding:4px;")
        a_lay.addWidget(self.lbl_apercu_titre)
        self.apercu_html = QTextEdit()
        self.apercu_html.setReadOnly(True)
        self.apercu_html.setStyleSheet(f"background:{C_CARD};border:1px solid {C_BORDER};border-radius:10px;")
        ombre_apercu = QGraphicsDropShadowEffect(self.apercu_html)
        ombre_apercu.setBlurRadius(0); ombre_apercu.setOffset(0, 3)
        ombre_apercu.setColor(QColor(31, 45, 80, 30))
        self.apercu_html.setGraphicsEffect(ombre_apercu)
        a_lay.addWidget(self.apercu_html)
        self.editor_split.addWidget(self.apercu_widget)
        self.editor_split.setSizes([500, 0])

        # --- Barre d'etat bas ---
        self.status_bar = QWidget()
        self.status_bar.setFixedHeight(28)
        self.status_bar.setStyleSheet(f"background:{C_BG_SOFT};border-top:1px solid {C_BORDER};border-radius:0 0 8px 8px;")
        sb_lay = QHBoxLayout(self.status_bar)
        sb_lay.setContentsMargins(10, 0, 10, 0)
        self.lbl_etat = QLabel()
        self.lbl_etat.setStyleSheet(f"color:{C_TEXT_SECONDARY};font-size:12px;")
        sb_lay.addWidget(self.lbl_etat)
        sb_lay.addStretch(1)
        self.lbl_mots = QLabel("0 mots")
        self.lbl_mots.setStyleSheet(f"color:{C_TEXT_SECONDARY};font-size:11px;")
        sb_lay.addWidget(self.lbl_mots)
        self.lbl_curseur = QLabel("Ligne 1, Col 1")
        self.lbl_curseur.setStyleSheet(f"color:{C_TEXT_SECONDARY};font-size:11px;")
        sb_lay.addWidget(self.lbl_curseur)
        d_lay.addWidget(self.status_bar)

        # --- Barre d'actions bas (2 lignes pour éviter le chevauchement) ---
        act1 = QHBoxLayout()
        act1.setSpacing(8)
        act1.addStretch(1)
        act1.addWidget(_btn("Apercu PDF", self._apercu,
                           _simple_btn_style(bg=C_BG_SOFT, fg=C_TEXT_SECONDARY,
                                             border=C_BORDER)))
        act1.addWidget(_btn("Generer (ecole)", self._generer_ecole,
                           _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY,
                                             border=C_BORDER)))
        d_lay.addLayout(act1)

        act2 = QHBoxLayout()
        act2.setSpacing(8)
        act2.addStretch(1)
        act2.addWidget(_btn("Generer pour un eleve...", self._generer_eleve,
                           _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY,
                                             border=C_BORDER)))
        act2.addWidget(_btn("Generer pour une classe...", self._generer_classe,
                           _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY,
                                             border=C_BORDER)))
        act2.addWidget(_btn("Enregistrer (Ctrl+S)", self._enregistrer,
                           _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY_PRESSED,
                                             border=C_BORDER)))
        d_lay.addLayout(act2)

        self.splitter.addWidget(droite)
        self.splitter.setSizes([300, 700])

        # Raccourcis clavier
        self._installer_raccourcis()

        # Timer pour apercu temps réel
        self._timer_apercu = QTimer()
        self._timer_apercu.setSingleShot(True)
        self._timer_apercu.setInterval(800)
        self._timer_apercu.timeout.connect(self._maj_apercu_temps_reel)

        self._recharger_liste()
        self._recharger_favoris()
        self._actualiser_etat()

    # ------------------------------------------------------------------
    def _actualiser_etat(self):
        if self._selection is None:
            self.lbl_etat.setText("Aucun modele selectionne. Cliquez sur « Nouveau ».")
            self.editeur.setPlainText("")
            self.editeur.setEnabled(False)
        else:
            marqueur = " *" if self._modifie else ""
            self.lbl_etat.setText(f"Modele : {self._selection}{marqueur}")
            self.editeur.setEnabled(True)

    def _recharger_liste(self, selection=None):
        self.liste.blockSignals(True)
        self.liste.clear()
        for modele in modele_svc.lister_modeles():
            item = QListWidgetItem(modele["nom"])
            item.setData(Qt.UserRole, modele["nom"])
            # Tooltip avec infos
            st = modele.get("date")
            if st:
                item.setToolTip(f"Modifie le : {st.strftime('%d/%m/%Y %H:%M')} | {modele.get('taille', 0)} octets")
            self.liste.addItem(item)
            if modele["nom"] == selection:
                self.liste.setCurrentItem(item)
        self.liste.blockSignals(False)
        if self.liste.currentItem() is None and self.liste.count():
            self.liste.setCurrentRow(0)
        if self.liste.currentItem() is None:
            self._selection = None
            self._modifie = False
            self._actualiser_etat()

    def _recharger_favoris(self):
        """Charge la liste des favoris depuis les parametres."""
        self.liste_favoris.blockSignals(True)
        self.liste_favoris.clear()
        favoris = modele_svc.get_favoris()
        for nom in favoris:
            item = QListWidgetItem(f"\u2605 {nom}")
            item.setData(Qt.UserRole, nom)
            self.liste_favoris.addItem(item)
        self.liste_favoris.blockSignals(False)

    def _filtrer_modeles(self, texte):
        """Filtre la liste des modeles en temps reel."""
        texte = texte.lower().strip()
        for i in range(self.liste.count()):
            item = self.liste.item(i)
            nom = item.data(Qt.UserRole).lower()
            item.setHidden(texte not in nom)

    def _charger(self, nom):
        self._selection = nom
        self._modifie = False
        contenu = modele_svc.lire_modele(nom) or ""
        # Charger un document declenche textChanged / currentCharFormatChanged :
        # on coupe les signaux pour ne pas marquer le modele comme modifie.
        self.editeur.blockSignals(True)
        try:
            if contenu.strip().startswith("<"):
                self.editeur.setHtml(contenu)
            else:
                self.editeur.setPlainText(contenu)
        finally:
            self.editeur.blockSignals(False)
        self._actualiser_etat()
        self._mettre_a_jour_compteur_mots()

    def _changer_modele(self, actuel, _previous):
        if actuel is None:
            return
        if self._modifie and self._selection is not None:
            rep = QMessageBox.question(
                self, "Modifications non enregistrees",
                f"Enregistrer les modifications de « {self._selection} » ?",
                QMessageBox.Save | QMessageBox.Discard, QMessageBox.Save)
            if rep == QMessageBox.Save:
                self._enregistrer()
            elif rep == QMessageBox.Discard:
                pass
            else:
                item = self.liste.findItems(self._selection, Qt.MatchExactly)
                if item:
                    self.liste.setCurrentItem(item[0])
                return
        self._charger(actuel.data(Qt.UserRole))
        self._actualiser_etat()

    def _changer_modele_favori(self, actuel, _previous):
        if actuel is None:
            return
        self._charger(actuel.data(Qt.UserRole))
        self._actualiser_etat()

    def _marquer_modifie(self):
        if self._selection is not None:
            self._modifie = True
            self._actualiser_etat()
        self._timer_apercu.start()  # Declencher apercu temps reel
        self._mettre_a_jour_compteur_mots()

    def _mettre_a_jour_compteur_mots(self):
        """Met a jour le compteur de mots dans la barre d'etat."""
        texte = self.editeur.toPlainText()
        mots = len(texte.split()) if texte.strip() else 0
        self.lbl_mots.setText(f"{mots} mot{'s' if mots > 1 else ''}")

    def _update_cursor_info(self):
        """Met a jour la position du curseur dans la barre d'etat."""
        curseur = self.editeur.textCursor()
        block = curseur.blockNumber() + 1
        col = curseur.columnNumber() + 1
        self.lbl_curseur.setText(f"Ligne {block}, Col {col}")

    # ------------------------------------------------------------------
    # Formatage de texte (editeur « type Word »)
    # ------------------------------------------------------------------
    def _construire_barre_outils(self):
        """Construit la barre d'outils style ruban Word."""
        tb = self.toolbar
        
        # Groupe 1: Fichier
        self._ajouter_action_tb("Nouveau", "fa5s.file", self._nouveau, "Ctrl+N")
        self._ajouter_action_tb("Ouvrir", "fa5s.folder-open", self._ouvrir_modele, "Ctrl+O")
        self._ajouter_action_tb("Enregistrer", "fa5s.save", self._enregistrer, "Ctrl+S")
        tb.addSeparator()
        
        # Groupe 2: Edition
        self._ajouter_action_tb("Annuler", "fa5s.undo", self.editeur.undo, "Ctrl+Z")
        self._ajouter_action_tb("Retablir", "fa5s.redo", self.editeur.redo, "Ctrl+Y")
        tb.addSeparator()
        self._ajouter_action_tb("Couper", "fa5s.cut", self.editeur.cut, "Ctrl+X")
        self._ajouter_action_tb("Copier", "fa5s.copy", self.editeur.copy, "Ctrl+C")
        self._ajouter_action_tb("Coller", "fa5s.paste", self.editeur.paste, "Ctrl+V")
        tb.addSeparator()
        self._ajouter_action_tb("Rechercher/Remplacer", "fa5s.search", self._rechercher_remplacer, "Ctrl+F")
        tb.addSeparator()
        
        # Groupe 3: Formatage caractere
        self.btn_gras = self._ajouter_action_tb_checkable("Gras", "fa5s.bold", self._activer_gras, "Ctrl+B", checkable=True)
        self.btn_italique = self._ajouter_action_tb_checkable("Italique", "fa5s.italic", self._activer_italique, "Ctrl+I", checkable=True)
        self.btn_souligne = self._ajouter_action_tb_checkable("Souligne", "fa5s.underline", self._activer_souligne, "Ctrl+U", checkable=True)
        self.btn_barré = self._ajouter_action_tb_checkable("Barré", "fa5s.strikethrough", self._activer_barre, checkable=True)
        tb.addSeparator()
        
        # Couleur texte / surlignage
        self._ajouter_action_tb("Couleur texte", "fa5s.font", self._choisir_couleur_texte)
        self._ajouter_action_tb("Surligner", "fa5s.highlighter", self._choisir_surlignage)
        tb.addSeparator()
        
        # Groupe 4: Paragraphe
        self._ajouter_action_tb("Align. gauche", "fa5s.align-left", lambda: self._aligner(Qt.AlignLeft), "Ctrl+L")
        self._ajouter_action_tb("Centrer", "fa5s.align-center", lambda: self._aligner(Qt.AlignHCenter), "Ctrl+E")
        self._ajouter_action_tb("Align. droite", "fa5s.align-right", lambda: self._aligner(Qt.AlignRight), "Ctrl+R")
        self._ajouter_action_tb("Justifier", "fa5s.align-justify", lambda: self._aligner(Qt.AlignJustify), "Ctrl+J")
        tb.addSeparator()
        self._ajouter_action_tb("Puces", "fa5s.list-ul", self._basculer_puces)
        self._ajouter_action_tb("Numérotation", "fa5s.list-ol", self._basculer_numerotation)
        self._ajouter_action_tb("Retrait +", "fa5s.indent", self._augmenter_retrait)
        self._ajouter_action_tb("Retrait -", "fa5s.outdent", self._diminuer_retrait)
        tb.addSeparator()
        
        # Groupe 5: Insertion
        self.combo_var = QComboBox()
        self.combo_var.addItem("Insérer variable...", None)
        for cle, libelle in modele_svc.variables():
            self.combo_var.addItem(f"{{{{{cle}}}}} - {libelle}", cle)
        self.combo_var.currentIndexChanged.connect(self._inserer_variable)
        self.combo_var.setMinimumWidth(200)
        self.combo_var.setMaximumWidth(250)
        tb.addWidget(self.combo_var)
        
        self._ajouter_action_tb("Image", "fa5s.image", self._inserer_image)
        self._ajouter_action_tb("Tableau", "fa5s.table", self._inserer_tableau)
        self._ajouter_action_tb("Séparateur", "fa5s.minus", self._inserer_separateur)
        self._ajouter_action_tb("Saut de page", "fa5s.file-alt", self._inserer_saut_page)
        tb.addSeparator()
        
        # Groupe 6: Styles rapides
        self.combo_style = QComboBox()
        self.combo_style.addItems([
            "Style normal", "Titre 1", "Titre 2", "Titre 3",
            "Sous-titre", "Citation", "Code", "Petit texte"
        ])
        self.combo_style.currentIndexChanged.connect(self._appliquer_style)
        self.combo_style.setFixedWidth(140)
        tb.addWidget(self.combo_style)
        
        # Taille police
        self.combo_taille = QComboBox()
        self.combo_taille.addItems([str(n) for n in (8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72)])
        self.combo_taille.setCurrentText("11")
        self.combo_taille.setFixedWidth(60)
        self.combo_taille.currentTextChanged.connect(self._choisir_taille)
        tb.addWidget(self.combo_taille)
        tb.addSeparator()
        
        # Groupe 7: Affichage
        self._ajouter_action_tb_checkable("Aperçu temps réel", "fa5s.eye", self._basculer_apercu, checkable=True)
        self._ajouter_action_tb("Plein écran", "fa5s.expand", self._basculer_plein_ecran)

    def _ajouter_action_tb(self, texte, icone, slot, raccourci=None):
        """Ajoute une action simple a la toolbar."""
        try:
            import qtawesome as qta
            action = QAction(qta.icon(icone, color=C_TEXT_SECONDARY), texte, self)
        except ImportError:
            action = QAction(texte, self)
        if raccourci:
            action.setShortcut(raccourci)
            action.setShortcutContext(Qt.WidgetShortcut)
        action.triggered.connect(slot)
        self.toolbar.addAction(action)
        return action

    def _ajouter_action_tb_checkable(self, texte, icone, slot, raccourci=None, checkable=False):
        """Ajoute une action checkable a la toolbar."""
        try:
            import qtawesome as qta
            action = QAction(qta.icon(icone, color=C_TEXT_SECONDARY), texte, self)
        except ImportError:
            action = QAction(texte, self)
        action.setCheckable(checkable)
        if raccourci:
            action.setShortcut(raccourci)
            action.setShortcutContext(Qt.WidgetShortcut)
        action.triggered.connect(slot)
        self.toolbar.addAction(action)
        return action

    def _activer_gras(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold
                          if self.btn_gras.isChecked() else QFont.Normal)
        self.editeur.mergeCurrentCharFormat(fmt)
        self.editeur.setFocus()

    def _activer_italique(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.btn_italique.isChecked())
        self.editeur.mergeCurrentCharFormat(fmt)
        self.editeur.setFocus()

    def _activer_souligne(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.btn_souligne.isChecked())
        self.editeur.mergeCurrentCharFormat(fmt)
        self.editeur.setFocus()

    def _choisir_taille(self, texte):
        try:
            taille = int(texte)
        except (TypeError, ValueError):
            return
        fmt = QTextCharFormat()
        fmt.setFontPointSize(taille)
        self.editeur.mergeCurrentCharFormat(fmt)

    def _aligner(self, align):
        from PyQt5.QtGui import QTextBlockFormat
        bf = QTextBlockFormat()
        bf.setAlignment(align)
        curseur = self.editeur.textCursor()
        curseur.mergeBlockFormat(bf)
        self.editeur.setFocus()

    def _basculer_puces(self):
        curseur = self.editeur.textCursor()
        if curseur.currentList() is not None:
            curseur.currentList().remove(curseur.block())
        else:
            curseur.createList(QTextListFormat.ListDisc)

    def _inserer_image(self):
        chemin, _ = QFileDialog.getOpenFileName(
            self, "Insérer une image", "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp);;Tous les fichiers (*)")
        if not chemin:
            return
        from PyQt5.QtGui import QPixmap
        pix = QPixmap(chemin)
        if pix.isNull():
            QMessageBox.warning(self, "Image",
                                "Le fichier choisi ne peut pas etre lu comme "
                                "une image.")
            return
        if max(pix.width(), pix.height()) > 1200:
            pix = pix.scaled(1200, 1200, Qt.KeepAspectRatio,
                             Qt.SmoothTransformation)
        # L'image doit etre encodee en data URI : un simple insertImage(pix)
        # laisserait un identifiant de ressource interne que le HTML/PDF ne
        # sait pas resoudre.
        import base64
        tampon = QBuffer()
        tampon.open(QIODevice.WriteOnly)
        pix.save(tampon, "PNG")
        uri = ("data:image/png;base64,"
               + base64.b64encode(bytes(tampon.data())).decode())
        fmt = QTextImageFormat()
        fmt.setName(uri)
        fmt.setWidth(pix.width())
        fmt.setHeight(pix.height())
        self.editeur.textCursor().insertImage(fmt)
        self.editeur.setFocus()

    def _sync_format(self, fmt):
        if fmt is None or not self.editeur.isEnabled():
            return
        self.btn_gras.setChecked(fmt.fontWeight() >= QFont.Bold)
        self.btn_italique.setChecked(fmt.fontItalic())
        self.btn_souligne.setChecked(fmt.fontUnderline())
        self.btn_barré.setChecked(fmt.fontStrikeOut())
        taille = fmt.fontPointSize()
        if taille > 0:
            try:
                self.combo_taille.setCurrentText(
                    str(int(round(taille))))
            except ValueError:
                pass

    # ================================================================
    # NOUVELLES METHODES POUR LA BARRE D'OUTILS COMPLETE
    # ================================================================

    def _activer_barre(self):
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(self.btn_barré.isChecked())
        self.editeur.mergeCurrentCharFormat(fmt)
        self.editeur.setFocus()

    def _choisir_couleur_texte(self):
        couleur = QColorDialog.getColor(QColor("#1D1D1F"), self, "Couleur du texte")
        if couleur.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(couleur)
            self.editeur.mergeCurrentCharFormat(fmt)
            self.editeur.setFocus()

    def _choisir_surlignage(self):
        couleur = QColorDialog.getColor(QColor("#FFF3CD"), self, "Couleur de surlignage")
        if couleur.isValid():
            fmt = QTextCharFormat()
            fmt.setBackground(couleur)
            self.editeur.mergeCurrentCharFormat(fmt)
            self.editeur.setFocus()

    def _basculer_numerotation(self):
        curseur = self.editeur.textCursor()
        if curseur.currentList() is not None:
            curseur.currentList().remove(curseur.block())
        else:
            curseur.createList(QTextListFormat.ListDecimal)

    def _augmenter_retrait(self):
        curseur = self.editeur.textCursor()
        bf = QTextBlockFormat()
        bf.setIndent(bf.indent() + 1)
        curseur.mergeBlockFormat(bf)
        self.editeur.setFocus()

    def _diminuer_retrait(self):
        curseur = self.editeur.textCursor()
        bf = QTextBlockFormat()
        bf.setIndent(max(0, bf.indent() - 1))
        curseur.mergeBlockFormat(bf)
        self.editeur.setFocus()

    def _inserer_tableau(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QSpinBox, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Insérer un tableau")
        dlg.setMinimumWidth(300)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        lignes = QSpinBox(); lignes.setRange(1, 50); lignes.setValue(3)
        colonnes = QSpinBox(); colonnes.setRange(1, 20); colonnes.setValue(3)
        form.addRow("Lignes :", lignes)
        form.addRow("Colonnes :", colonnes)
        lay.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec_() == QDialog.Accepted:
            curseur = self.editeur.textCursor()
            table = curseur.insertTable(lignes.value(), colonnes.value())
            fmt = QTextTableFormat()
            fmt.setBorder(1)
            fmt.setBorderStyle(QTextTableFormat.BorderStyle_Solid)
            fmt.setCellPadding(4)
            fmt.setCellSpacing(0)
            fmt.setWidth(QTextTableFormat.Length(QTextTableFormat.PercentageLength, 100))
            table.setFormat(fmt)
            self.editeur.setFocus()

    def _inserer_separateur(self):
        curseur = self.editeur.textCursor()
        curseur.insertHtml("<hr style='border:0;border-top:1px solid #C9C9D2;margin:12px 0;'>")
        self.editeur.setFocus()

    def _inserer_saut_page(self):
        curseur = self.editeur.textCursor()
        curseur.insertHtml("<div style='page-break-after:always;'></div>")
        self.editeur.setFocus()

    def _appliquer_style(self, index):
        styles = {
            0: ("Normal", 11, QFont.Normal, False, False, Qt.AlignLeft),
            1: ("Titre 1", 24, QFont.Bold, False, False, Qt.AlignLeft),
            2: ("Titre 2", 20, QFont.Bold, False, False, Qt.AlignLeft),
            3: ("Titre 3", 16, QFont.Bold, False, False, Qt.AlignLeft),
            4: ("Sous-titre", 13, QFont.Normal, True, False, Qt.AlignLeft),
            5: ("Citation", 11, QFont.Normal, True, False, Qt.AlignLeft),
            6: ("Code", 10, QFont.Normal, False, False, Qt.AlignLeft),
            7: ("Petit texte", 9, QFont.Normal, False, False, Qt.AlignLeft),
        }
        if index in styles:
            nom, taille, poids, italique, _, align = styles[index]
            curseur = self.editeur.textCursor()
            cf = QTextCharFormat()
            cf.setFontPointSize(taille)
            cf.setFontWeight(poids)
            cf.setFontItalic(italique)
            if index == 6:  # Code
                cf.setFontFamily("Monospace")
                cf.setBackground(QColor("#F2F2F5"))
            curseur.mergeCharFormat(cf)
            bf = QTextBlockFormat()
            bf.setAlignment(align)
            if index == 5:  # Citation
                bf.setLeftMargin(40)
                bf.setRightMargin(40)
            curseur.mergeBlockFormat(bf)
            self.combo_taille.setCurrentText(str(taille))
            self.editeur.setFocus()

    def _basculer_apercu(self, checked):
        self.apercu_widget.setVisible(checked)
        if checked:
            self._maj_apercu_temps_reel()

    def _basculer_plein_ecran(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _maj_apercu_temps_reel(self):
        """Met a jour l'aperçu HTML en temps reel."""
        html = self.editeur.toHtml()
        self.apercu_html.setHtml(html)

    def _menu_contextuel_liste(self, pos):
        item = self.liste.itemAt(pos)
        if not item:
            return
        nom = item.data(Qt.UserRole)
        menu = QMenu(self)
        act_fav = menu.addAction("\u2605 Ajouter aux favoris" if nom not in modele_svc.get_favoris() else "\u2605 Retirer des favoris")
        act_fav.triggered.connect(lambda: self._basculer_favori(nom))
        menu.addSeparator()
        act_dup = menu.addAction("Dupliquer")
        act_dup.triggered.connect(lambda: self._dupliquer_specific(nom))
        act_ren = menu.addAction("Renommer")
        act_ren.triggered.connect(lambda: self._editer_nom(nom))
        act_sup = menu.addAction("Supprimer")
        act_sup.triggered.connect(lambda: self._supprimer_specific(nom))
        menu.exec_(self.liste.mapToGlobal(pos))

    def _menu_contextuel_favori(self, pos):
        item = self.liste_favoris.itemAt(pos)
        if not item:
            return
        nom = item.data(Qt.UserRole)
        menu = QMenu(self)
        act_ret = menu.addAction("\u2605 Retirer des favoris")
        act_ret.triggered.connect(lambda: self._basculer_favori(nom))
        menu.exec_(self.liste_favoris.mapToGlobal(pos))

    def _basculer_favori(self, nom):
        favoris = modele_svc.get_favoris()
        if nom in favoris:
            favoris.remove(nom)
            toast.info(self, f"Retiré des favoris : {nom}")
        else:
            favoris.append(nom)
            toast.succes(self, f"Ajouté aux favoris : {nom}")
        modele_svc.set_favoris(favoris)
        self._recharger_favoris()

    def _dupliquer_specific(self, nom):
        contenu = modele_svc.lire_modele(nom)
        if contenu is None:
            return
        i = 1
        existants = {m["nom"] for m in modele_svc.lister_modeles()}
        while f"{nom} (copie {i})" in existants:
            i += 1
        copie = f"{nom} (copie {i})"
        modele_svc.ecrire_modele(copie, contenu)
        self._recharger_liste(selection=copie)
        toast.succes(self, "Modele duplique.")

    def _supprimer_specific(self, nom):
        rep = QMessageBox.question(
            self, "Supprimer le modele",
            f"Supprimer definitivement le modele « {nom} » ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if rep != QMessageBox.Yes:
            return
        modele_svc.supprimer_modele(nom)
        self._recharger_liste()
        self._recharger_favoris()
        toast.succes(self, "Modele supprime.")

    def _ouvrir_modele(self):
        """Ouvre un modele existant (double-clic ou Ctrl+O)."""
        if self._selection:
            self._charger(self._selection)

    def _rechercher_remplacer(self):
        """Dialogue recherche/remplace."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QCheckBox, QDialogButtonBox, QHBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Rechercher / Remplacer")
        dlg.setMinimumWidth(400)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        self.recherche_texte = QLineEdit()
        self.remplace_texte = QLineEdit()
        self.casse_sensible = QCheckBox("Respecter la casse")
        self.mot_entier = QCheckBox("Mot entier seulement")
        form.addRow("Rechercher :", self.recherche_texte)
        form.addRow("Remplacer par :", self.remplace_texte)
        lay.addLayout(form)
        opts = QHBoxLayout()
        opts.addWidget(self.casse_sensible)
        opts.addWidget(self.mot_entier)
        lay.addLayout(opts)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(lambda: self._executer_recherche_remplacer(dlg))
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        dlg.exec_()

    def _executer_recherche_remplacer(self, dlg):
        texte = self.recherche_texte.text()
        remplace = self.remplace_texte.text()
        if not texte:
            return
        flags = 0
        if self.casse_sensible.isChecked():
            flags |= Qt.CaseSensitive
        if self.mot_entier.isChecked():
            flags |= Qt.FindWholeWords
        curseur = self.editeur.textCursor()
        curseur.beginEditBlock()
        trouve = False
        while self.editeur.find(texte, flags):
            curseur = self.editeur.textCursor()
            if curseur.hasSelection():
                curseur.insertText(remplace)
                trouve = True
        curseur.endEditBlock()
        if not trouve:
            toast.info(self, f"Aucune occurrence de « {texte} » trouvee.")
        dlg.accept()

    def _importer_modele(self):
        chemin, _ = QFileDialog.getOpenFileName(
            self, "Importer un modele", "",
            "HTML (*.html *.htm);;Tous les fichiers (*)")
        if not chemin:
            return
        try:
            contenu = Path(chemin).read_text(encoding="utf-8")
            nom = Path(chemin).stem
            i = 1
            existants = {m["nom"] for m in modele_svc.lister_modeles()}
            base = nom
            while nom in existants:
                nom = f"{base} ({i})"
                i += 1
            modele_svc.ecrire_modele(nom, contenu)
            self._recharger_liste(selection=nom)
            self._charger(nom)
            toast.succes(self, f"Modele importe : {nom}")
        except Exception as exc:
            QMessageBox.warning(self, "Import", f"Erreur : {exc}")

    def _exporter_modele(self):
        if self._selection is None:
            toast.info(self, "Selectionnez un modele a exporter.")
            return
        chemin, _ = QFileDialog.getSaveFileName(
            self, "Exporter le modele", f"{self._selection}.html",
            "HTML (*.html);;Tous les fichiers (*)")
        if not chemin:
            return
        try:
            contenu = self.editeur.toHtml()
            Path(chemin).write_text(contenu, encoding="utf-8")
            toast.succes(self, f"Modele exporte : {chemin}")
        except Exception as exc:
            QMessageBox.warning(self, "Export", f"Erreur : {exc}")

    def _installer_raccourcis(self):
        """Installe les raccourcis clavier supplementaires."""
        raccourcis = [
            ("Ctrl+N", self._nouveau),
            ("Ctrl+O", self._ouvrir_modele),
            ("Ctrl+S", self._enregistrer),
            ("Ctrl+P", self._apercu),
            ("Ctrl+F", self._rechercher_remplacer),
            ("Ctrl+B", lambda: self.btn_gras.setChecked(not self.btn_gras.isChecked()) or self._activer_gras()),
            ("Ctrl+I", lambda: self.btn_italique.setChecked(not self.btn_italique.isChecked()) or self._activer_italique()),
            ("Ctrl+U", lambda: self.btn_souligne.setChecked(not self.btn_souligne.isChecked()) or self._activer_souligne()),
            ("Ctrl+L", lambda: self._aligner(Qt.AlignLeft)),
            ("Ctrl+E", lambda: self._aligner(Qt.AlignHCenter)),
            ("Ctrl+R", lambda: self._aligner(Qt.AlignRight)),
            ("Ctrl+J", lambda: self._aligner(Qt.AlignJustify)),
        ]
        for sequence, slot in raccourcis:
            sc = QShortcut(QKeySequence(sequence), self)
            sc.setContext(Qt.WidgetShortcut)
            sc.activated.connect(slot)

    # ------------------------------------------------------------------
    def _verifier_modifie_avant_quitter(self):
        if self._modifie and self._selection is not None:
            rep = QMessageBox.question(
                self, "Modifications non enregistrees",
                f"Enregistrer les modifications de « {self._selection} » ?",
                QMessageBox.Save | QMessageBox.Discard, QMessageBox.Save)
            if rep == QMessageBox.Save:
                return self._enregistrer()
            if rep == QMessageBox.Discard:
                return True
            return False
        return True

    def reject(self):
        if self._verifier_modifie_avant_quitter():
            super().reject()

    # ------------------------------------------------------------------
    def _enregistrer(self):
        nom = self._selection
        if nom is None:
            QMessageBox.information(self, "Modele",
                                    "Creez d'abord un modele avec « Nouveau ».")
            return False
        texte = self.editeur.toHtml()
        if not self.editeur.toPlainText().strip():
            texte = ""
        try:
            modele_svc.ecrire_modele(nom, texte)
        except ValueError as exc:
            QMessageBox.warning(self, "Modele", str(exc))
            return False
        self._modifie = False
        self._actualiser_etat()
        toast.succes(self, f"Modele « {nom} » enregistre.")
        return True

    def _nouveau(self):
        if self._modifie and self._selection is not None:
            if not self._verifier_modifie_avant_quitter():
                return
        base = "Modele"
        i = 1
        existants = {m["nom"] for m in modele_svc.lister_modeles()}
        while f"{base} {i}" in existants:
            i += 1
        nom = f"{base} {i}"
        modele_svc.ecrire_modele(nom, modele_svc.MODELE_DEFAUT)
        self._recharger_liste(selection=nom)
        self._charger(nom)
        self._editer_nom(nom)

    def _editer_nom(self, nom):
        nouveau, ok = QInputDialog.getText(
            self, "Renommer le modele", "Nom du modele :", text=nom)
        if not ok:
            return
        nouveau = nouveau.strip()
        if not nouveau or nouveau == nom:
            return
        try:
            modele_svc.renommer_modele(nom, nouveau)
        except (ValueError, FileExistsError, FileNotFoundError) as exc:
            QMessageBox.warning(self, "Modele", str(exc))
            return
        self._selection = nouveau
        self._modifie = False
        self._recharger_liste(selection=nouveau)
        self._actualiser_etat()
        toast.succes(self, "Modele renomme.")

    def _renommer(self):
        if self._selection is None:
            return
        if not self._verifier_modifie_avant_quitter():
            return
        self._editer_nom(self._selection)

    def _dupliquer(self):
        if self._selection is None:
            return
        if not self._verifier_modifie_avant_quitter():
            return
        nom = self._selection
        i = 1
        existants = {m["nom"] for m in modele_svc.lister_modeles()}
        while f"{nom} (copie {i})" in existants:
            i += 1
        copie = f"{nom} (copie {i})"
        modele_svc.ecrire_modele(copie, self.editeur.toHtml())
        self._recharger_liste(selection=copie)
        self._charger(copie)
        toast.succes(self, "Modele duplique.")

    def _supprimer(self):
        if self._selection is None:
            return
        nom = self._selection
        rep = QMessageBox.question(
            self, "Supprimer le modele",
            f"Supprimer definitivement le modele « {nom} » ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if rep != QMessageBox.Yes:
            return
        modele_svc.supprimer_modele(nom)
        self._recharger_liste()
        toast.succes(self, "Modele supprime.")

    def _inserer_variable(self, index):
        if index <= 0:
            return
        cle = self.combo_var.currentData()
        self.combo_var.setCurrentIndex(0)
        if cle:
            curseur = self.editeur.textCursor()
            curseur.insertText("{{" + cle + "}}")

    # ------------------------------------------------------------------
    def _ouvrir_fichier(self, chemin):
        try:
            _ouvrir_pdf(chemin)
        except Exception as exc:
            QMessageBox.warning(self, "Document", f"Erreur d'ouverture : {exc}")

    def _generer(self, eleve_id=None, classe_id=None, cible=False):
        if self._selection is None:
            QMessageBox.information(self, "Modele",
                                    "Selectionnez d'abord un modele.")
            return
        if self._modifie:
            if not self._enregistrer():
                return
        try:
            chemin = modele_svc.generer_pdf(
                self._selection, eleve_id=eleve_id, classe_id=classe_id,
                cible=cible, ouvrir=False)
        except (ValueError, FileNotFoundError) as exc:
            QMessageBox.warning(self, "Generation", str(exc))
            return
        toast.succes(self, "PDF genere dans l'Espace Documents.")
        self._ouvrir_fichier(chemin)

    def _generer_eleve(self):
        eleves = repos.eleves()
        if not eleves:
            QMessageBox.information(self, "Generation",
                                    "Aucun eleve dans la base.")
            return
        if self._selection is None:
            QMessageBox.information(self, "Modele", "Selectionnez un modele.")
            return
        if self._modifie and not self._enregistrer():
            return
        choix = _dialogue_eleve(self, eleves, "Generer le document pour un eleve")
        if choix is _ANNULE or choix is None:
            return
        self._generer(eleve_id=choix, cible=False)

    def _generer_classe(self):
        if self._selection is None:
            QMessageBox.information(self, "Modele", "Selectionnez un modele.")
            return
        if self._modifie and not self._enregistrer():
            return
        choix = _dialogue_classe(self, "Generer le document pour une classe")
        if choix is _ANNULE:
            return
        self._generer(classe_id=choix, cible=False)

    def _generer_ecole(self):
        self._generer(cible=True)

    def _apercu(self):
        if self._selection is None:
            QMessageBox.information(self, "Modele", "Selectionnez un modele.")
            return
        if self._modifie and not self._enregistrer():
            return
        try:
            chemin = modele_svc.apercu_modele(self._selection)
        except (ValueError, FileNotFoundError) as exc:
            QMessageBox.warning(self, "Apercu", str(exc))
            return
        self._ouvrir_fichier(chemin)


def ouvrir_modeles(page, ctx):
    """Point d'entree : fenetre des modeles (reservee au directeur)."""
    fenetre = FenetreModeles(page, ctx)
    fenetre.exec_()