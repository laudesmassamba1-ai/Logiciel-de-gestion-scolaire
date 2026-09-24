from functools import partial

import datetime
import json
import os
from pathlib import Path

from PyQt5.QtCore import QDate, Qt, QUrl
from PyQt5.QtGui import QColor, QPixmap, QDesktopServices
from PyQt5.QtWidgets import (
    QDialog, QFileDialog, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QComboBox, QPushButton, QVBoxLayout, QTabWidget,
    QWidget, QTableWidget, QTableWidgetItem, QScrollArea, QFrame, QGridLayout,
    QHeaderView, QStackedWidget, QFormLayout, QTextEdit, QGroupBox,
    QSizePolicy,
)

from repositories import repos
from services import pdf_export, photos, reports
from services.assistant_ia import apprentissage_rapide
from ui import toast
from ui import icons
from ui.loader import apply_ui
from ui.pages.helpers import (
    _btn, _simple_btn_style, _classe_items, _reload_combo,
    _parse_money, refuser_si_hors_annee, _actions_cell, _adapter_hauteur,
    _empty_state, _appreciation, _make_table, _fill_combos,
)
from ui.widgets import KPICard, fmt_money
from ui.widgets.page_templates import ListPageTemplate
from core.config import (
    C_PRIMARY, C_PRIMARY_LIGHT, C_PRIMARY_PRESSED, C_BLUE, C_BLUE_LIGHT,
    C_BLUE_BORDER, C_RED, C_RED_BG,
    C_RED_BORDER, C_BG_SOFT, C_BORDER, C_TEXT_SECONDARY, C_TEXT,
    C_GREEN, C_GREEN_BG, C_BORDER_STRONG, C_CARD, C_GRID, FONT_DISPLAY_FAMILY,
    C_TEXT_MUTED, C_AURORA,
    C_ACCENT_VIOLET, C_VIOLET_LIGHT, C_VIOLET_PRESSED,
    STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY, PERIODES, DOCS_DIR,
    lire_composant,
)
from resources.design_tokens import Colors


def eleves(page, ctx):
    if page.layout() is not None:
        return
    tpl = ListPageTemplate(
        page, "Eleves",
        "Effectifs de toute l'ecole - filtrez par classe pour plus de lisibilite")

    search = QLineEdit()
    search.setPlaceholderText("Rechercher (nom, prenom, matricule)...")
    search.setMaximumWidth(360)
    combo_classe = QComboBox()
    combo_statut = QComboBox()
    combo_statut.addItems(["Tous les statuts", "Inscrit", "Pre-inscrit", "Inactif"])
    tpl.ajouter_filtre(search)
    tpl.ajouter_filtre(combo_classe)
    tpl.ajouter_filtre(combo_statut)
    tpl.ajouter_space_filtre()

    kpi = [
        tpl.ajouter_kpi(KPICard("Total eleves", "0", Colors.PRIMARY), 0),
        tpl.ajouter_kpi(KPICard("Pre-inscrits", "0", Colors.WARNING), 1),
        tpl.ajouter_kpi(KPICard("Inscrits", "0", Colors.INFO), 2),
        tpl.ajouter_kpi(KPICard("Inactifs", "0", Colors.DANGER), 3),
    ]
    tpl.table.setColumnCount(8)
    tpl.table.setHorizontalHeaderLabels(
        ["Matricule", "Nom complet", "Classe", "Sexe", "Naissance",
         "Tel tuteur", "Statut", "Actions"])

    def _ouvrir_inscription(eleve=None):
        open_inscription_dialog(page, ctx, eleve)
        fill()

    def _delete_eleve(parent, ctx, eleve):
        from ui.pages.helpers import confirmer
        if confirmer(
                parent,
                f"Supprimer l'élève {eleve['prenom']} {eleve['nom']} ?\n\n"
                "Attention : ses notes, presences et paiements seront "
                "également supprimés.",
                "Supprimer"):
            repos.delete_eleve(eleve["id"])
            fill()

    def _ouvrir_detail_eleve(parent, ctx, eleve):
        """Ouvre une fenêtre complète avec toutes les infos de l'élève - version modernisée."""
        dlg = QDialog(parent)
        dlg.setWindowTitle(f"Fiche élève - {eleve['prenom']} {eleve['nom']} ({eleve['matricule']})")
        dlg.resize(1200, 850)
        dlg.setMinimumSize(950, 700)
        dlg.setStyleSheet(f"""
            QDialog {{ {C_AURORA} }}
            QTabWidget::pane {{ border: 1px solid {C_BORDER}; background: {C_CARD}; border-radius: 0 0 12px 12px; }}
            QTabBar::tab {{
                background: {C_BG_SOFT}; color: {C_TEXT_SECONDARY}; padding: 12px 24px;
                border: 1px solid {C_BORDER}; border-bottom: none; border-top-left-radius: 8px;
                border-top-right-radius: 8px; margin-right: 2px; font-weight: 700; font-size: 12px;
            }}
            QTabBar::tab:selected {{ background: {C_CARD}; color: {C_PRIMARY_PRESSED}; border-bottom: 1px solid {C_CARD}; }}
            QTabBar::tab:hover {{ background: {C_BORDER}; color: {C_TEXT}; }}
            QTableWidget {{ gridline-color: {C_GRID}; alternate-background-color: {C_BG_SOFT}; }}
            QTableWidget::item {{ padding: 8px 10px; border-bottom: 1px solid {C_GRID}; }}
            QHeaderView::section {{ background: {C_BG_SOFT}; color: {C_TEXT_SECONDARY}; font-weight: 700; font-size: 11px; letter-spacing: 0.6px; text-transform: uppercase; padding: 10px 10px; border: none; border-bottom: 2px solid {C_BORDER_STRONG}; }}
        """)
        
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ===== HEADER STICKY AVEC PHOTO & INFOS =====
        header = QFrame()
        # Hauteur MINIMALE (et non fixe) : le contenu (nom 24 px, badges,
        # contacts, actions) fixe sa propre hauteur sans jamais se
        # chevaucher ni rogner les boutons de droite.
        header.setMinimumHeight(170)
        # Hauteur NATURELLE (pas de surplus absorbe) : le contenu fixe sa
        # propre hauteur sans chevauchement et sans trou sous les actions.
        header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {C_CARD}, stop:1 {C_BG_SOFT}); border-bottom: 1px solid {C_BORDER};")
        # Ombre douce-dure : détache l'header du contenu (effet « sticker »).
        _ombre_header = QGraphicsDropShadowEffect(header)
        _ombre_header.setBlurRadius(5)
        _ombre_header.setOffset(0, 3)
        _ombre_header.setColor(QColor(31, 45, 80, 30))
        header.setGraphicsEffect(_ombre_header)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)
        header_layout.setSpacing(20)
        
        # Photo circulaire
        photo_lbl = QLabel()
        photo_lbl.setFixedSize(120, 120)
        photo_lbl.setAlignment(Qt.AlignCenter)
        photo_lbl.setStyleSheet(f"""
            background: {C_BG_SOFT}; 
            border: 3px solid {C_PRIMARY_LIGHT}; 
            border-radius: 60px;
        """)
        _ombre_photo = QGraphicsDropShadowEffect(photo_lbl)
        _ombre_photo.setBlurRadius(0)
        _ombre_photo.setOffset(0, 4)
        _ombre_photo.setColor(QColor(31, 45, 80, 45))
        photo_lbl.setGraphicsEffect(_ombre_photo)
        pix = photos.pixmap_photo(eleve)
        if pix:
            # Avatar rond : recadre au centre et masque circulaire, pour
            # qu'une photo non carree remplisse proprement le conteneur
            # (ni debordement, ni coins carres visibles).
            photo_lbl.setPixmap(photos.pixmap_rond(pix, 114))
        else:
            # Initiales au lieu de texte "Photo"
            initiales = (eleve['prenom'][0] + eleve['nom'][0]).upper() if eleve['prenom'] and eleve['nom'] else "?"
            photo_lbl.setText(initiales)
            photo_lbl.setStyleSheet(photo_lbl.styleSheet() + f" font-size: 36px; font-weight: 700; color: {C_PRIMARY_PRESSED};")
        header_layout.addWidget(photo_lbl)
        
        # Infos principales
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        
        nom_complet = QLabel(f"<span style='font-family: \"{FONT_DISPLAY_FAMILY}\", Inter, \"Noto Color Emoji\", sans-serif; font-size: 24px; font-weight: 800; letter-spacing: -0.3px; color: {C_TEXT};'>{eleve['prenom']} {eleve['nom']}</span>")
        info_layout.addWidget(nom_complet)
        
        matricule_ligne = QWidget()
        matricule_lay = QHBoxLayout(matricule_ligne)
        matricule_lay.setContentsMargins(0, 2, 0, 2)
        matricule_lay.setSpacing(6)
        icone_mat = QLabel()
        icone_mat.setPixmap(icons.pixmap_icone("tag", couleur=C_PRIMARY_PRESSED, taille=14, widget=matricule_ligne))
        matricule_lay.addWidget(icone_mat)
        matricule_txt = QLabel(f"Matricule : <b>{eleve['matricule']}</b>")
        matricule_txt.setStyleSheet(f"color: {C_PRIMARY_PRESSED}; font-weight: 600; font-size: 13px;")
        matricule_lay.addWidget(matricule_txt)
        info_layout.addWidget(matricule_ligne)
        
        classe_nom = eleve.get('classe_nom') or "—"
        statut = eleve.get('statut') or "—"
        sexe = eleve.get('sexe') or "—"
        naissance = eleve.get('date_naissance') or "—"
        
        # Badges style pour les infos clés
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(8)
        
        def _badge(picto, label, value):
            # Badge « perle » : pictogramme vectoriel (fiable, aucune police
            # emoji requise) + texte, alignes horizontalement.
            cell = QWidget()
            lay = QHBoxLayout(cell)
            lay.setContentsMargins(14, 5, 14, 5)
            lay.setSpacing(8)
            icone_lbl = QLabel()
            icone_lbl.setPixmap(icons.pixmap_icone(picto, couleur=C_PRIMARY, taille=15, widget=cell))
            lay.addWidget(icone_lbl)
            texte = QLabel(f"<span style='color: {C_TEXT_SECONDARY};'>{label} :</span> <b style='color: {C_TEXT};'>{value}</b>")
            lay.addWidget(texte)
            cell.setStyleSheet(f"""
                background: {C_CARD};
                border: 1px solid {C_BORDER};
                border-radius: 22px;
            """)
            ombre_b = QGraphicsDropShadowEffect(cell)
            ombre_b.setBlurRadius(0)
            ombre_b.setOffset(0, 2)
            ombre_b.setColor(QColor(31, 45, 80, 26))
            cell.setGraphicsEffect(ombre_b)
            return cell
        
        badges_layout.addWidget(_badge("classes", "Classe", classe_nom))
        badges_layout.addWidget(_badge("check", "Statut", statut))
        badges_layout.addWidget(_badge("user", "Sexe", "Fille" if sexe == "F" else "Garçon" if sexe == "M" else sexe))
        badges_layout.addWidget(_badge("calendrier", "Né le", naissance))
        badges_layout.addStretch(1)
        info_layout.addLayout(badges_layout)
        
        # Contacts
        tuteur = eleve.get('tuteur_nom') or eleve.get('pere_nom') or "—"
        tel = eleve.get('tuteur_tel') or eleve.get('pere_tel') or "—"
        mere = eleve.get('mere_nom') or "—"
        mere_tel = eleve.get('mere_tel') or "—"
        
        contacts_layout = QHBoxLayout()
        contacts_layout.setSpacing(12)
        contacts_layout.addWidget(_badge("personnel", "Tuteur", f"{tuteur} · {tel}"))
        if mere != "—":
            contacts_layout.addWidget(_badge("user", "Mère", f"{mere} · {mere_tel}"))
        contacts_layout.addStretch(1)
        info_layout.addLayout(contacts_layout)
        
        # Adresse
        adresse = eleve.get('adresse') or "—"
        adresse_ligne = QWidget()
        adresse_lay = QHBoxLayout(adresse_ligne)
        adresse_lay.setContentsMargins(0, 4, 0, 4)
        adresse_lay.setSpacing(8)
        icone_adr = QLabel()
        icone_adr.setPixmap(icons.pixmap_icone("map", couleur=C_TEXT_MUTED, taille=14, widget=adresse_ligne))
        adresse_lay.addWidget(icone_adr)
        addr_lbl = QLabel(adresse)
        addr_lbl.setWordWrap(True)
        addr_lbl.setStyleSheet(f"color: {C_TEXT_SECONDARY}; font-size: 12px;")
        adresse_lay.addWidget(addr_lbl, 1)
        info_layout.addWidget(adresse_ligne)
        
        info_layout.addStretch(1)
        header_layout.addLayout(info_layout, 1)
        
        # Boutons actions header (vertical)
        actions_header = QVBoxLayout()
        actions_header.setSpacing(8)
        actions_header.setAlignment(Qt.AlignTop | Qt.AlignRight)
        
        def _btn_action(text, callback, primary=False, picto="edit", couleur=None):
            btn = _btn(f"{text}",
                       callback,
                       _simple_btn_style(
                           bg=C_PRIMARY if primary else C_BLUE_LIGHT,
                           fg=C_CARD if primary else C_BLUE,
                           border=C_PRIMARY if primary else C_BLUE_BORDER
                       ))
            btn.setIcon(icons.icone(picto, couleur=(C_CARD if primary else C_BLUE), taille=15))
            btn.setMinimumWidth(160)
            return btn
        
        actions_header.addWidget(_btn_action("Modifier", lambda: _modifier_depuis_detail(dlg, eleve), picto="edit"))
        actions_header.addWidget(_btn_action("Bulletin PDF", lambda: _generer_bulletin_eleve(dlg, eleve), primary=True, picto="pdf"))
        actions_header.addWidget(_btn_action("Certificat", lambda: _generer_certificat_eleve(dlg, eleve), picto="award"))
        actions_header.addWidget(_btn_action("Reçu paiement", lambda: _generer_recu_eleve(dlg, eleve), picto="money"))
        actions_header.addStretch(1)
        header_layout.addLayout(actions_header)
        
        layout.addWidget(header)
        
        # ===== ONGLETS =====
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        
        # Onglet 1 : Notes & Moyennes
        tab_notes = _creer_onglet_notes(eleve)
        tabs.addTab(tab_notes, icons.icone("stats", couleur=C_TEXT_SECONDARY, taille=16), "Notes & Moyennes")
        
        # Onglet 2 : Documents (avec association)
        tab_docs = _creer_onglet_documents(eleve)
        tabs.addTab(tab_docs, icons.icone("documents", couleur=C_TEXT_SECONDARY, taille=16), "Documents")
        
        # Onglet 3 : Emploi du temps
        tab_edt = _creer_onglet_edt(eleve)
        tabs.addTab(tab_edt, icons.icone("planning", couleur=C_TEXT_SECONDARY, taille=16), "Emploi du temps")
        
        # Onglet 4 : Présences
        tab_pres = _creer_onglet_presences(eleve)
        tabs.addTab(tab_pres, icons.icone("presences", couleur=C_TEXT_SECONDARY, taille=16), "Présences")
        
        # Onglet 5 : Paiements
        tab_paiements = _creer_onglet_paiements(eleve)
        tabs.addTab(tab_paiements, icons.icone("money", couleur=C_TEXT_SECONDARY, taille=16), "Paiements")
        
        layout.addWidget(tabs)
        
        # ===== BARRE BASSE =====
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(16, 12, 16, 12)
        btn_row.addStretch(1)
        
        # Stats rapides en bas à gauche
        stats_lbl = QLabel(_generer_stats_rapides(eleve))
        stats_lbl.setStyleSheet(f"color: {C_TEXT_SECONDARY}; font-size: 12px;")
        btn_row.addWidget(stats_lbl)
        btn_row.addStretch(1)
        
        btn_fermer = _btn("Fermer", dlg.accept, STYLE_BTN_SECONDARY)
        btn_fermer.setMinimumWidth(120)
        btn_row.addWidget(btn_fermer)
        layout.addLayout(btn_row)
        
        dlg.exec_()

    def _modifier_depuis_detail(dlg, eleve):
        dlg.accept()
        open_inscription_dialog(dlg.parent(), ctx, eleve)

    def _generer_bulletin_eleve(dlg, eleve):
        from services import pdf_export
        try:
            pdf_export.bulletin_pdf(eleve)
            toast.succes(dlg, "Bulletin généré dans l'Espace Documents.")
        except Exception as e:
            from ui.pages.helpers import confirmer
            QMessageBox.warning(dlg, "Bulletin", f"Erreur : {e}")

    def _generer_certificat_eleve(dlg, eleve):
        from services import pdf_export
        try:
            pdf_export.certificat_scolarite_pdf(eleve, repos.parametres())
            toast.succes(dlg, "Certificat généré dans l'Espace Documents.")
        except Exception as e:
            QMessageBox.warning(dlg, "Certificat", f"Erreur : {e}")

    def _generer_recu_eleve(dlg, eleve):
        from services import pdf_export
        try:
            # Récupérer le dernier paiement pour générer le reçu
            paiements = repos.paiements(nom=eleve['nom'], prenom=eleve['prenom'])
            if not paiements:
                toast.info(dlg, "Aucun paiement trouvé pour générer un reçu.")
                return
            dernier = max(paiements, key=lambda p: (p.get('date_paiement', ''), p.get('id', 0)))
            pdf_export.recu_paiement_pdf(
                {"prenom": eleve['prenom'], "nom": eleve['nom'], "matricule": eleve['matricule']},
                float(dernier.get('montant', 0) or 0),
                dernier.get('mode_reglement', 'Espèces'),
                dernier.get('reference', '')
            )
            toast.succes(dlg, "Reçu généré dans l'Espace Documents.")
        except Exception as e:
            QMessageBox.warning(dlg, "Reçu", f"Erreur : {e}")

    def _generer_stats_rapides(eleve):
        """Génère un résumé HTML des stats rapides pour l'élève."""
        from core.config import C_PRIMARY_PRESSED, C_TEXT_SECONDARY, C_GREEN, C_RED, C_TEXT
        # Moyenne
        from services.assistant_ia import AssistantIA
        # On évite de créer une instance complète, on calcule direct
        parts = []
        parts.append(f"<span style='color: {C_PRIMARY_PRESSED};'>Matricule : {eleve['matricule']}</span>")
        
        # Statut
        statut = eleve.get('statut', '—')
        color_statut = C_GREEN if statut == 'Inscrit' else C_RED if statut == 'Inactif' else C_PRIMARY_PRESSED
        parts.append(f"<span style='color: {color_statut};'>Statut : {statut}</span>")
        
        # Classe
        if eleve.get('classe_nom'):
            parts.append(f"<span style='color: {C_TEXT_SECONDARY};'>Classe : {eleve['classe_nom']}</span>")
        
        # Dernier paiement
        paiements = repos.paiements(nom=eleve['nom'], prenom=eleve['prenom']) if hasattr(repos, 'paiements') else []
        if paiements:
            dernier = max(paiements, key=lambda p: (p.get('date_paiement', ''), p.get('id', 0)))
            montant = float(dernier.get('montant', 0) or 0)
            date_p = dernier.get('date_paiement', '')[:10]
            parts.append(f"<span style='color: {C_GREEN};'>Paiement : {montant:,.0f} FCFA le {date_p}</span>")
        else:
            parts.append(f"<span style='color: {C_TEXT_SECONDARY};'>Aucun paiement</span>")
        
        # Solde
        solde_info = repos.solde_eleve(eleve["id"]) if hasattr(repos, 'solde_eleve') else {"solde": 0}
        solde = float(solde_info.get('solde', 0) or 0)
        color_solde = C_GREEN if solde <= 0 else C_RED
        parts.append(f"<span style='color: {color_solde};'>Solde : {solde:+,.0f} FCFA</span>")
        
        return "  •  ".join(parts)

    def _associer_document(eleve):
        """Ouvre un sélecteur de fichier pour associer un document à l'élève."""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        import shutil
        from core.config import DOCS_DIR
        
        chemin, _ = QFileDialog.getOpenFileName(
            None, "Choisir un document à associer", "",
            "PDF (*.pdf);;Images (*.png *.jpg *.jpeg);;Tous (*)")
        if not chemin:
            return
        
        # Copier vers DOCS_DIR avec nom incluant le matricule
        import os
        ext = os.path.splitext(chemin)[1]
        base = os.path.basename(chemin).replace(ext, "")
        # Nettoyer le nom de base
        import re
        base = re.sub(r'[^\w\-_]', '_', base)[:50]
        nouveau_nom = f"{base}_{eleve['matricule']}{ext}"
        dest = DOCS_DIR / nouveau_nom
        
        # Gérer les doublons
        counter = 1
        while dest.exists():
            nouveau_nom = f"{base}_{eleve['matricule']}_{counter}{ext}"
            dest = DOCS_DIR / nouveau_nom
            counter += 1
        
        try:
            shutil.copy2(chemin, dest)
            toast.succes(None, f"Document associé : {nouveau_nom}")
        except Exception as e:
            QMessageBox.warning(None, "Erreur", f"Impossible d'associer : {e}")

    def _associer_document_fichier(eleve, chemin_fichier):
        """Associe un fichier existant à l'élève en le renommant."""
        import os
        import shutil
        from core.config import DOCS_DIR
        from PyQt5.QtWidgets import QMessageBox
        
        ext = os.path.splitext(chemin_fichier)[1]
        base = os.path.basename(chemin_fichier).replace(ext, "")
        import re
        base = re.sub(r'[^\w\-_]', '_', base)[:50]
        nouveau_nom = f"{base}_{eleve['matricule']}{ext}"
        dest = DOCS_DIR / nouveau_nom
        
        counter = 1
        while dest.exists():
            nouveau_nom = f"{base}_{eleve['matricule']}_{counter}{ext}"
            dest = DOCS_DIR / nouveau_nom
            counter += 1
        
        try:
            shutil.copy2(chemin_fichier, dest)
            toast.succes(None, f"Document associé : {nouveau_nom}")
        except Exception as e:
            QMessageBox.warning(None, "Erreur", f"Impossible d'associer : {e}")

    def _dissocier_document(eleve, chemin_fichier):
        """Dissocie un document de l'élève en supprimant le matricule du nom."""
        import os
        from core.config import DOCS_DIR
        from PyQt5.QtWidgets import QMessageBox
        
        try:
            src = DOCS_DIR / os.path.basename(chemin_fichier)
            if not src.exists():
                toast.info(None, "Fichier déjà déplacé ou supprimé")
                return
            
            # Nouveau nom sans le matricule
            nom = src.stem
            if eleve['matricule'] in nom:
                nom = nom.replace(f"_{eleve['matricule']}", "")
            dest = DOCS_DIR / f"{nom}{src.suffix}"
            
            counter = 1
            while dest.exists():
                dest = DOCS_DIR / f"{nom}_{counter}{src.suffix}"
                counter += 1
            
            src.rename(dest)
            toast.succes(None, f"Document dissocié : {dest.name}")
        except Exception as e:
            QMessageBox.warning(None, "Erreur", f"Impossible de dissocier : {e}")

    def _creer_onglet_notes(eleve):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Sélecteur de période
        from PyQt5.QtWidgets import QComboBox
        periode_combo = QComboBox()
        periode_combo.addItems(["T1", "T2", "T3", "Toutes"])
        periode_combo.setCurrentText("Toutes")
        layout.addWidget(QLabel("Période :"))
        layout.addWidget(periode_combo)
        
        # Table des notes
        from ui.widgets import DataTable
        table = DataTable()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Matière", "Devoir 1", "Devoir 2", "Composition", "Moyenne"])
        # Largeurs suffisantes : le header uppercase ne doit jamais etre
        # coupe ("COMPOSITI..." a la place de "COMPOSITION").
        table.setColumnWidth(0, 200)
        table.setColumnWidth(1, 100)
        table.setColumnWidth(2, 100)
        table.setColumnWidth(3, 150)
        table.setColumnWidth(4, 110)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        
        # Moyennes par matière + générale
        moyennes_frame = QFrame()
        moyennes_frame.setStyleSheet(f"background: {C_BG_SOFT}; border: 1px solid {C_BORDER}; border-radius: 10px;")
        moyennes_layout = QVBoxLayout(moyennes_frame)
        lbl_moyennes = QLabel("Moyennes par matière")
        lbl_moyennes.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {C_PRIMARY_PRESSED};")
        moyennes_layout.addWidget(lbl_moyennes)
        lbl_moyenne_gen = QLabel("Moyenne générale : —")
        lbl_moyenne_gen.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {C_TEXT};")
        moyennes_layout.addWidget(lbl_moyenne_gen)
        layout.addWidget(moyennes_frame)
        
        def charger_notes():
            table.setRowCount(0)
            periode = periode_combo.currentText()
            if periode == "Toutes":
                # Récupérer toutes les notes
                rows = repos.notes_eleve(eleve["id"], None) if hasattr(repos, 'notes_eleve') else []
            else:
                rows = repos.notes_eleve(eleve["id"], periode)
            
            # Grouper par matière
            by_matiere = {}
            for n in rows:
                mat = n.get('matiere_nom', 'Matière')
                if mat not in by_matiere:
                    by_matiere[mat] = []
                by_matiere[mat].append(n)
            
            for mat, notes in by_matiere.items():
                # Calculer moyennes
                d1_vals = [float(n.get('devoir1', 0) or 0) for n in notes]
                d2_vals = [float(n.get('devoir2', 0) or 0) for n in notes]
                comp_vals = [float(n.get('composition', 0) or 0) for n in notes]
                moy_d1 = sum(d1_vals)/len(d1_vals) if d1_vals else 0
                moy_d2 = sum(d2_vals)/len(d2_vals) if d2_vals else 0
                moy_comp = sum(comp_vals)/len(comp_vals) if comp_vals else 0
                moy_mat = (moy_d1 + moy_d2 + moy_comp) / 3
                
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(mat))
                table.setItem(row, 1, QTableWidgetItem(f"{moy_d1:.2f}" if d1_vals else "—"))
                table.setItem(row, 2, QTableWidgetItem(f"{moy_d2:.2f}" if d2_vals else "—"))
                table.setItem(row, 3, QTableWidgetItem(f"{moy_comp:.2f}" if comp_vals else "—"))
                table.setItem(row, 4, QTableWidgetItem(f"{moy_mat:.2f}"))
            
            # Moyenne générale
            if by_matiere:
                all_moy = []
                for notes in by_matiere.values():
                    for n in notes:
                        d1 = float(n.get('devoir1', 0) or 0)
                        d2 = float(n.get('devoir2', 0) or 0)
                        comp = float(n.get('composition', 0) or 0)
                        all_moy.append((d1 + d2 + comp) / 3)
                if all_moy:
                    lbl_moyenne_gen.setText(f"Moyenne générale : {sum(all_moy)/len(all_moy):.2f} / 20")
                else:
                    lbl_moyenne_gen.setText("Moyenne générale : —")
            else:
                lbl_moyenne_gen.setText("Moyenne générale : —")
        
        periode_combo.currentTextChanged.connect(charger_notes)
        charger_notes()
        
        return widget

    def _creer_onglet_documents(eleve):
        """Onglet Documents : liste + association de nouveaux documents à l'élève."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Barre d'outils
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        
        btn_ajouter = _btn("Associer un document", lambda: _associer_document(eleve),
                          _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY_PRESSED, border=C_BLUE_BORDER))
        btn_ajouter.setIcon(icons.icone("plus", couleur=C_PRIMARY_PRESSED, taille=15))
        toolbar.addWidget(btn_ajouter)
        
        btn_actualiser = _btn("Actualiser", lambda: charger_docs(),
                             _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER))
        btn_actualiser.setIcon(icons.icone("refresh", couleur=C_BLUE, taille=15))
        toolbar.addWidget(btn_actualiser)
        
        toolbar.addStretch(1)
        
        # Filtre type
        from PyQt5.QtWidgets import QComboBox
        filtre_combo = QComboBox()
        filtre_combo.addItems(["Tous", "Bulletin", "Reçu", "Certificat", "Emploi du temps", "Autres"])
        filtre_combo.setFixedWidth(180)
        toolbar.addWidget(QLabel("Filtrer :"))
        toolbar.addWidget(filtre_combo)
        
        layout.addLayout(toolbar)
        
        from ui.widgets import DataTable
        table = DataTable()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Type", "Nom", "Date", "Taille", "Élève", "Actions"])
        # La colonne Nom (fichiers longs) s'etire; Actions garde une largeur
        # suffice pour les boutons sans les ecraser.
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setColumnWidth(0, 90)
        table.setColumnWidth(2, 130)
        table.setColumnWidth(3, 80)
        table.setColumnWidth(4, 110)
        table.setColumnWidth(5, 220)
        layout.addWidget(table)
        
        def charger_docs():
            table.setRowCount(0)
            from core.config import DOCS_DIR
            if not DOCS_DIR.exists():
                return
            
            import datetime
            filtre_type = filtre_combo.currentText()
            matricule = eleve['matricule']
            nom_eleve = eleve['nom'].lower()
            
            for p in sorted(DOCS_DIR.rglob("*.pdf"), key=lambda x: x.stat().st_mtime, reverse=True):
                st = p.stat()
                
                # Déterminer le type
                type_doc = "Autres"
                for prefixe, label in [("bulletins_", "Bulletin"), ("recu_", "Reçu"), ("certificat_", "Certificat"), ("planning_", "Emploi du temps"), ("paie", "Paie")]:
                    if p.name.lower().startswith(prefixe):
                        type_doc = label
                        break
                
                # Filtrer par type si nécessaire
                if filtre_type != "Tous" and type_doc != filtre_type:
                    continue
                
                # Vérifier si associé à cet élève
                associe = matricule.lower() in p.name.lower() or nom_eleve in p.name.lower()
                
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(type_doc))
                table.setItem(row, 1, QTableWidgetItem(p.name))
                table.setItem(row, 2, QTableWidgetItem(datetime.datetime.fromtimestamp(st.st_mtime).strftime("%d/%m/%Y %H:%M")))
                table.setItem(row, 3, QTableWidgetItem(f"{st.st_size/1024:.1f} Ko"))
                table.setItem(row, 4, QTableWidgetItem("✓ Oui" if associe else "—"))
                
                # Actions
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(4)
                
                btn_ouvrir = _btn("Ouvrir", lambda _, path=str(p): pdf_export._ouvrir_pdf(path),
                                 _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER, compact=True))
                actions_layout.addWidget(btn_ouvrir)
                
                if not associe:
                    btn_assoc = _btn("Associer", lambda _, path=str(p): _associer_document_fichier(eleve, path),
                                    _simple_btn_style(bg=C_GREEN_BG, fg=C_GREEN, border=C_GREEN, compact=True))
                    actions_layout.addWidget(btn_assoc)
                else:
                    # Option pour dissocier (renommer le fichier)
                    btn_dissoc = _btn("Dissocier", lambda _, path=str(p): _dissocier_document(eleve, path),
                                     _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED, compact=True))
                    actions_layout.addWidget(btn_dissoc)
                
                table.setCellWidget(row, 5, actions_widget)
        
        filtre_combo.currentTextChanged.connect(charger_docs)
        charger_docs()
        return widget

    def _creer_onglet_edt(eleve):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        from ui.widgets import DataTable
        table = DataTable()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Jour", "Créneau", "Matière", "Salle", "Enseignant"])
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        
        def charger_edt():
            table.setRowCount(0)
            classe_id = eleve.get('classe_id')
            if not classe_id:
                layout.addWidget(QLabel("Aucune classe assignée"))
                return
            
            planning = repos.planning_for(classe_id) if hasattr(repos, 'planning_for') else {}
            jours_ordre = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
            creneaux_ordre = ["08h-09h", "09h-10h", "10h-11h", "11h-12h", "12h-13h", "13h-14h", "14h-15h", "15h-16h", "16h-17h"]
            
            for jour in jours_ordre:
                for creneau in creneaux_ordre:
                    key = (jour, creneau)
                    if key in planning:
                        entry = planning[key]
                        row = table.rowCount()
                        table.insertRow(row)
                        table.setItem(row, 0, QTableWidgetItem(jour))
                        table.setItem(row, 1, QTableWidgetItem(creneau))
                        table.setItem(row, 2, QTableWidgetItem(entry.get('matiere', '')))
                        table.setItem(row, 3, QTableWidgetItem(entry.get('salle', '')))
                        # Trouver l'enseignant
                        matiere_nom = entry.get('matiere', '')
                        ens = ""
                        if matiere_nom:
                            mat = repos.matiere_by_nom(matiere_nom) if hasattr(repos, 'matiere_by_nom') else None
                            if mat and mat.get('id'):
                                ens_id = repos.enseignant_par_matiere(mat['id']) if hasattr(repos, 'enseignant_par_matiere') else None
                                if ens_id:
                                    ens_row = repos.enseignant_by_id(ens_id) if hasattr(repos, 'enseignant_by_id') else None
                                    ens = f"{ens_row.get('prenom','')} {ens_row.get('nom','')}" if ens_row else ""
                        table.setItem(row, 4, QTableWidgetItem(ens))
        charger_edt()
        return widget

    def _creer_onglet_presences(eleve):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        from ui.widgets import DataTable
        table = DataTable()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Date", "Statut", "Justifié", "Motif"])
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        
        # Stats
        stats_frame = QFrame()
        stats_frame.setStyleSheet(f"background: {C_BG_SOFT}; border: 1px solid {C_BORDER}; border-radius: 10px;")
        stats_layout = QHBoxLayout(stats_frame)
        lbl_present = QLabel("Présent : 0")
        lbl_absent = QLabel("Absent : 0")
        lbl_retard = QLabel("Retard : 0")
        lbl_total = QLabel("Total : 0")
        for lbl in [lbl_present, lbl_absent, lbl_retard, lbl_total]:
            lbl.setStyleSheet(f"font-weight: bold; color: {C_TEXT};")
            stats_layout.addWidget(lbl)
        layout.addWidget(stats_frame)
        
        def charger_presences():
            table.setRowCount(0)
            presences = repos.presences_eleve(eleve["id"]) if hasattr(repos, 'presences_eleve') else []
            p_count = a_count = r_count = 0
            for p in presences:
                statut = p.get('statut', '')
                if statut == 'Present':
                    p_count += 1
                elif statut == 'Absent':
                    a_count += 1
                elif statut == 'En retard':
                    r_count += 1
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(p.get('date', '')))
                table.setItem(row, 1, QTableWidgetItem(statut))
                table.setItem(row, 2, QTableWidgetItem(p.get('justifie', 'Non')))
                table.setItem(row, 3, QTableWidgetItem(p.get('motif', '')))
            lbl_present.setText(f"Présent : {p_count}")
            lbl_absent.setText(f"Absent : {a_count}")
            lbl_retard.setText(f"Retard : {r_count}")
            lbl_total.setText(f"Total : {len(presences)}")
        
        charger_presences()
        return widget

    def _creer_onglet_paiements(eleve):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        from ui.widgets import DataTable
        table = DataTable()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Date", "Type", "Montant", "Mode", "Trimestre", "Mois"])
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        
        # Solde
        solde_frame = QFrame()
        solde_frame.setStyleSheet(f"background: {C_BG_SOFT}; border: 1px solid {C_BORDER}; border-radius: 10px;")
        solde_layout = QHBoxLayout(solde_frame)
        lbl_attendu = QLabel("Attendu : 0 FCFA")
        lbl_paye = QLabel("Payé : 0 FCFA")
        lbl_solde = QLabel("Solde : 0 FCFA")
        for lbl in [lbl_attendu, lbl_paye, lbl_solde]:
            lbl.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {C_TEXT};")
            solde_layout.addWidget(lbl)
        layout.addWidget(solde_frame)
        
        def charger_paiements():
            table.setRowCount(0)
            paiements = repos.paiements(nom=eleve['nom'], prenom=eleve['prenom'])
            total = 0
            for p in paiements:
                total += float(p.get('montant', 0) or 0)
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(p.get('date_paiement', '')[:10] if p.get('date_paiement') else ''))
                table.setItem(row, 1, QTableWidgetItem(p.get('type_frais', '')))
                table.setItem(row, 2, QTableWidgetItem(fmt_money(p.get('montant', 0))))
                table.setItem(row, 3, QTableWidgetItem(p.get('mode_reglement', '')))
                table.setItem(row, 4, QTableWidgetItem(p.get('trimestre', '') or ''))
                table.setItem(row, 5, QTableWidgetItem(p.get('mois', '') or ''))
            
            # Solde
            solde_info = repos.solde_eleve(eleve["id"]) if hasattr(repos, 'solde_eleve') else {"attendu": 0, "paye": 0, "solde": 0}
            lbl_attendu.setText(f"Attendu : {fmt_money(solde_info.get('attendu', 0))}")
            lbl_paye.setText(f"Payé : {fmt_money(solde_info.get('paye', 0))}")
            lbl_solde.setText(f"Solde : {fmt_money(solde_info.get('solde', 0))}")
        
        charger_paiements()
        return widget

    def fill():
        _reload_combo(combo_classe, _classe_items())
        classe_id = combo_classe.currentData()
        statut = combo_statut.currentText()
        recherche = search.text().strip()
        rows = repos.eleves(classe_id=classe_id, statut=statut, recherche=recherche)
        valeurs = [[e["matricule"], f"{e['prenom']} {e['nom']}",
                    e["classe_nom"] or "-", e["sexe"] or "-",
                    e["date_naissance"] or "-", e["tuteur_tel"] or "-",
                    e["statut"], ""] for e in rows]
        tpl.remplir(
            valeurs,
            message_vide="Aucun eleve trouve",
            sous_titre_vide="Modifiez votre recherche ou changez de filtre.")
        # Composant themable "eleves_table" : QSS cible du tableau.
        comp_tab = lire_composant("eleves_table")
        tpl.table.setStyleSheet(
            tpl.table.styleSheet()
            + " QTableWidget { alternate-background-color: "
            + comp_tab["fond_alternat"] + "; border: 1px solid "
            + comp_tab["bordure"] + "; gridline-color: "
            + comp_tab["grille"] + "; }"
            + " QHeaderView::section { background: "
            + comp_tab["fond_entete"] + "; color: "
            + comp_tab["texte_entete"] + "; }")
        # Colonne Statut : couleurs du composant "statuts".
        comp_stat = lire_composant("statuts")
        _couleur_statut = {
            "Inscrit": comp_stat["present"],
            "Pre-inscrit": comp_stat["du"],
            "Inactif": comp_stat["absent"],
        }
        for i, e in enumerate(rows):
            item = tpl.table.item(i, 6)
            if item is not None:
                from PyQt5.QtGui import QColor
                item.setForeground(QColor(
                    _couleur_statut.get(e["statut"], comp_stat["du"])))
            tpl.table.setCellWidget(i, 7, _actions_cell(
                _btn("Détails", partial(_ouvrir_detail_eleve, page, ctx, e),
                     _simple_btn_style(bg=C_GREEN_BG, fg=C_GREEN, border=C_BORDER, compact=True)),
                _btn("Modifier", partial(open_inscription_dialog, page, ctx, e),
                     _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER, compact=True)),
                _btn("Supprimer", partial(_delete_eleve, page, ctx, e),
                     _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER, compact=True))))
        page._rows = rows

        eleves_all = repos.eleves(classe_id=classe_id)
        kpi[0].set_value(len(eleves_all))
        kpi[1].set_value(len([e for e in eleves_all if e["statut"] == "Pre-inscrit"]))
        kpi[2].set_value(len([e for e in eleves_all if e["statut"] == "Inscrit"]))
        kpi[3].set_value(len([e for e in eleves_all if e["statut"] == "Inactif"]))

        if classe_id:
            tpl.header.set_sous_titre(
                f"Effectifs et suivis scolaires - classe {combo_classe.currentText()}")
        else:
            tpl.header.set_sous_titre(
                "Effectifs de toute l'école - filtrez par classe pour plus de lisibilite")

    btn_add = _btn("+ Nouvel Eleve", lambda: _ouvrir_inscription(), STYLE_BTN_PRIMARY)
    tpl.header.ajouter_action(btn_add)
    btn_export = _btn("Exporter CSV",
                      lambda: reports.export_eleves_csv(getattr(page, "_rows", [])),
                      STYLE_BTN_SECONDARY)
    tpl.header.ajouter_action(btn_export)
    btn_pdf = _btn("Exporter PDF",
                   lambda: _exporter_pdf(), STYLE_BTN_SECONDARY)
    tpl.header.ajouter_action(btn_pdf)

    def _exporter_pdf():
        from services import rapports
        rows = getattr(page, "_rows", [])
        lignes = [[e["matricule"], f"{e['prenom']} {e['nom']}",
                   e["classe_nom"] or "-", e["sexe"] or "-",
                   e["date_naissance"] or "-", e["tuteur_tel"] or "-",
                   e["statut"]] for e in rows]
        if not rapports.export_table_pdf(
                "Liste des eleves",
                f"Filtres actuels - le {rapports._date_pdf()}",
                ["Matricule", "Nom complet", "Classe", "Sexe", "Naissance",
                 "Tel tuteur", "Statut"], lignes,
                "rapport_liste_eleves.pdf"):
            toast.info(page, "Rien a exporter : aucun eleve dans ce filtre.")

    def populate_class_combo():
        combo_classe.clear()
        combo_classe.addItem("Toutes les classes", None)
        for c in repos.classes():
            combo_classe.addItem(c["nom"], c["id"])
        if combo_classe.count() > 1:
            combo_classe.setCurrentIndex(1)

    populate_class_combo()

    search.textChanged.connect(fill)
    combo_classe.currentIndexChanged.connect(fill)
    combo_statut.currentIndexChanged.connect(fill)

    def double_clicked(row, _col):
        if 0 <= row < len(getattr(page, "_rows", [])):
            _ouvrir_inscription(page._rows[row])

    tpl.table.cellDoubleClicked.connect(double_clicked)
    tpl.table.setToolTip("Double-cliquez sur une ligne pour modifier le dossier")

    fill()
    page.refresh = fill


def open_inscription_dialog(parent, ctx, eleve=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Dossier d'Inscription")
    dlg.resize(1000, 780)
    dlg.setMinimumSize(800, 600)
    apply_ui("eleves/inscription.ui", dlg)
    dlg.btn_save.setStyleSheet(STYLE_BTN_PRIMARY)
    dlg.btn_cancel.setStyleSheet(STYLE_BTN_SECONDARY)

    # Fond transparent du scroll : selon le theme sombre du systeme, le
    # viewport du QScrollArea est sinon peint en noir et masque la lecture.
    dlg.scrollArea.viewport().setAutoFillBackground(False)
    dlg.scrollContent.setAutoFillBackground(False)

    lbl_matricule = QLabel()
    lbl_matricule.setStyleSheet(
        f"color: {C_PRIMARY}; font-weight: bold; font-size: 13px;")
    dlg.horizontalLayout_Header.addWidget(lbl_matricule)

    reins_row = QHBoxLayout()
    dlg.horizontalLayout_Header.addLayout(reins_row)
    input_reins = QLineEdit()
    input_reins.setPlaceholderText("Matricule (reinscription)")
    input_reins.setFixedWidth(160)
    btn_reins = _btn("Rechercher",
                     lambda: _load_reins(),
                      _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER))
    reins_row.addWidget(input_reins)
    reins_row.addWidget(btn_reins)

    # ---- Photo de l'eleve (stockee localement, non synchronisee) ----
    photo_state = {"nom": "", "source": None, "modifiee": False}

    photo_ligne = QHBoxLayout()
    photo_ligne.setSpacing(12)
    dlg.lbl_photo_preview = QLabel()
    dlg.lbl_photo_preview.setFixedSize(110, 130)
    dlg.lbl_photo_preview.setAlignment(Qt.AlignCenter)
    dlg.lbl_photo_preview.setStyleSheet(
        f"background: {C_BG_SOFT}; border: 1px dashed {C_BORDER};"
        f" border-radius: 12px; color: {C_TEXT_SECONDARY}; font-size: 12px;")
    dlg.lbl_photo_preview.setText("Photo\n(optionnel)")
    col_photo = QVBoxLayout()
    col_photo.setSpacing(8)
    lbl_photo_titre = QLabel("Photo de l'eleve")
    lbl_photo_titre.setStyleSheet(
        f"color: {C_PRIMARY_PRESSED}; font-weight: bold; font-size: 12px;")
    col_photo.addWidget(lbl_photo_titre)
    btn_choisir = _btn(
        "Choisir une photo...", lambda: _choisir_photo(),
        _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER))
    btn_retirer = _btn(
        "Retirer la photo", lambda: _retirer_photo(),
        _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER))
    col_photo.addWidget(btn_choisir)
    col_photo.addWidget(btn_retirer)
    col_photo.addStretch(1)
    photo_ligne.addWidget(dlg.lbl_photo_preview)
    photo_ligne.addLayout(col_photo)
    photo_ligne.addStretch(1)
    dlg.verticalLayout_Card1.addLayout(photo_ligne)

    def _afficher_apercu(pix):
        dlg.lbl_photo_preview.setText("")
        dlg.lbl_photo_preview.setPixmap(pix.scaled(
            dlg.lbl_photo_preview.size(), Qt.KeepAspectRatio,
            Qt.SmoothTransformation))

    def _choisir_photo():
        chemin, _ = QFileDialog.getOpenFileName(
            dlg, "Photo de l'eleve", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;Tous les fichiers (*)")
        if not chemin:
            return
        pix = QPixmap(chemin)
        if pix.isNull():
            QMessageBox.warning(dlg, "Photo",
                                "Ce fichier ne peut pas etre lu comme une image.")
            return
        photo_state["source"] = chemin
        photo_state["modifiee"] = True
        _afficher_apercu(pix)
        dlg.check_photos.setChecked(True)

    def _retirer_photo():
        photo_state["source"] = None
        photo_state["nom"] = ""
        photo_state["modifiee"] = True
        dlg.lbl_photo_preview.setPixmap(QPixmap())
        dlg.lbl_photo_preview.setText("Photo\n(optionnel)")
        dlg.check_photos.setChecked(False)

    def _initialiser_photo(source):
        photo_state["nom"] = source.get("photo") or ""
        photo_state["source"] = None
        photo_state["modifiee"] = False
        pix = photos.pixmap_photo(source)
        if pix:
            _afficher_apercu(pix)
            dlg.check_photos.setChecked(bool(source.get("check_photos")))
        else:
            dlg.lbl_photo_preview.setPixmap(QPixmap())
            dlg.lbl_photo_preview.setText("Photo\n(optionnel)")
            dlg.check_photos.setChecked(False)

    # ---- Chips « Apprendre à Charo » : retient des qualites sur l'eleve ----
    _STYLE_CHIP_IA = (
        f"QPushButton {{ background: {C_VIOLET_LIGHT}; color: {C_VIOLET_PRESSED};"
        f" border: 1px solid {C_ACCENT_VIOLET}; border-radius: 12px;"
        f" padding: 5px 12px; font-weight: 600; }}"
        f"QPushButton:hover {{ background: {C_ACCENT_VIOLET}; color: white; }}")

    def _apprendre(qualite):
        prenom = dlg.input_prenom.text().strip()
        nom = dlg.input_nom.text().strip()
        partie = " ".join(p for p in (prenom, nom) if p).strip()
        if not partie:
            QMessageBox.information(
                dlg, "Apprendre à Charo",
                "Renseignez d'abord le prenom (et le nom) de l'eleve.")
            return
        if apprentissage_rapide(ctx.user, prenom, nom, qualite):
            toast.succes(dlg, f"Charo a retenu : {partie} — {qualite}.")
        else:
            toast.succes(dlg, "Ce fait est deja connu de Charo.")

    rangee_ia = QHBoxLayout()
    rangee_ia.setSpacing(6)
    lbl_ia = QLabel("Apprendre à Charo :")
    lbl_ia.setStyleSheet(
        f"color: {C_PRIMARY_PRESSED}; font-weight: bold; font-size: 12px;")
    rangee_ia.addWidget(lbl_ia)
    for qualite in ("bon en maths", "bon en lecture", "tres serieux",
                    "a besoin d'encouragements", "sportif"):
        chip = QPushButton(qualite)
        chip.setCursor(Qt.PointingHandCursor)
        chip.setStyleSheet(_STYLE_CHIP_IA)
        chip.setFixedHeight(30)
        chip.clicked.connect(lambda _=False, q=qualite: _apprendre(q))
        rangee_ia.addWidget(chip)
    rangee_ia.addStretch(1)
    dlg.verticalLayout_Card1.addLayout(rangee_ia)

    def update_matricule():
        if not eleve:
            lbl_matricule.setText(f"Matricule : {repos.next_matricule()}")
        else:
            lbl_matricule.setText(f"Matricule : {eleve['matricule']}")

    # Dossier charge via la recherche de reinscription : dans ce cas on
    # MET A JOUR l'eleve existant au lieu de creer un doublon.
    reins_source = {"eleve": None}

    def _load_reins():
        found = repos.eleve_by_matricule(input_reins.text().strip())
        if not found:
            QMessageBox.warning(dlg, "Reinscription",
                                f"Aucun eleve trouve avec le matricule {input_reins.text().strip()}.")
            return
        reins_source["eleve"] = found
        _fill_from(found)
        dlg.radio_new.setChecked(False)
        dlg.radio_reins.setChecked(True)
        lbl_matricule.setText(f"Reinscription de {found['prenom']} {found['nom']} "
                              f"({found['matricule']})")
        input_reins.setEnabled(False)
        btn_reins.setEnabled(False)

    def _fill_from(source):
        dlg.input_nom.setText(source["nom"])
        dlg.input_prenom.setText(source["prenom"])
        sexe = f"Sexe : {source['sexe']}" if source["sexe"] else "Sexe : Masculin"
        idx = dlg.combo_sexe.findText(sexe)
        if idx >= 0:
            dlg.combo_sexe.setCurrentIndex(idx)
        if source["date_naissance"]:
            dlg.date_naissance.setDate(
                QDate.fromString(source["date_naissance"], "yyyy-MM-dd"))
        dlg.input_lieu_naiss.setText(source["lieu_naissance"] or "")
        dlg.input_ecole_provenance.setText(source["ecole_provenance"] or "")
        dlg.input_pere_nom.setText(source["pere_nom"] or "")
        dlg.input_pere_tel.setText(source["pere_tel"] or "")
        dlg.input_mere_nom.setText(source["mere_nom"] or "")
        dlg.input_mere_tel.setText(source["mere_tel"] or "")
        dlg.input_tuteur_nom.setText(source["tuteur_nom"] or "")
        dlg.input_tuteur_tel.setText(source["tuteur_tel"] or "")
        dlg.input_adresse_famille.setText(source["adresse"] or "")
        idx = dlg.combo_classe.findData(source["classe_id"])
        if idx >= 0:
            dlg.combo_classe.setCurrentIndex(idx)
        _initialiser_photo(source)

    def on_radio():
        is_reins = dlg.radio_reins.isChecked()
        input_reins.setEnabled(is_reins)
        btn_reins.setEnabled(is_reins)

    if eleve:
        dlg.setWindowTitle(f"Modifier - {eleve['prenom']} {eleve['nom']}")
        dlg.radio_new.setChecked(eleve["statut"] != "Pre-inscrit")
        dlg.radio_reins.setChecked(eleve["statut"] == "Pre-inscrit")
        dlg.input_nom.setText(eleve["nom"])
        dlg.input_prenom.setText(eleve["prenom"])
        sexe = f"Sexe : {eleve['sexe']}" if eleve["sexe"] else "Sexe : Masculin"
        idx = dlg.combo_sexe.findText(sexe)
        if idx >= 0:
            dlg.combo_sexe.setCurrentIndex(idx)
        if eleve["date_naissance"]:
            dlg.date_naissance.setDate(QDate.fromString(eleve["date_naissance"], "yyyy-MM-dd"))
        dlg.input_lieu_naiss.setText(eleve["lieu_naissance"] or "")
        dlg.input_ecole_provenance.setText(eleve["ecole_provenance"] or "")
        dlg.input_pere_nom.setText(eleve["pere_nom"] or "")
        dlg.input_pere_tel.setText(eleve["pere_tel"] or "")
        dlg.input_mere_nom.setText(eleve["mere_nom"] or "")
        dlg.input_mere_tel.setText(eleve["mere_tel"] or "")
        dlg.input_tuteur_nom.setText(eleve["tuteur_nom"] or "")
        dlg.input_tuteur_tel.setText(eleve["tuteur_tel"] or "")
        dlg.input_adresse_famille.setText(eleve["adresse"] or "")
        dlg.check_acte.setChecked(bool(eleve["check_acte"]))
        dlg.check_photos.setChecked(bool(eleve["check_photos"]))
        dlg.check_bulletin.setChecked(bool(eleve["check_bulletin"]))
        _initialiser_photo(eleve)
        dlg.input_montant_verse.setEnabled(False)
        dlg.combo_mode_reglement.setEnabled(False)
        dlg.btn_save.setText("Enregistrer les Modifications")
        input_reins.setEnabled(False)
        btn_reins.setEnabled(False)

    def refresh_classes(select_id=None):
        dlg.combo_classe.clear()
        for c in repos.classes():
            dlg.combo_classe.addItem(c["nom"], c["id"])
        if select_id is not None:
            idx = dlg.combo_classe.findData(select_id)
            if idx >= 0:
                dlg.combo_classe.setCurrentIndex(idx)

    refresh_classes(eleve["classe_id"] if eleve else None)

    def add_classe():
        from ui.pages.classes_page import open_classe_dialog
        open_classe_dialog(dlg, ctx, on_created=refresh_classes)

    dlg.btn_add_classe.clicked.connect(add_classe)
    dlg.radio_new.toggled.connect(lambda _: on_radio())
    dlg.radio_reins.toggled.connect(lambda _: on_radio())
    on_radio()
    update_matricule()


    def save():
        nom = dlg.input_nom.text().strip()
        prenom = dlg.input_prenom.text().strip()
        if not nom or not prenom:
            QMessageBox.warning(dlg, "Inscription",
                                "Le nom et le prenom sont obligatoires.")
            return
        classe_id = dlg.combo_classe.currentData()
        if not classe_id:
            QMessageBox.warning(dlg, "Inscription",
                                "Selectionnez une classe (ou creez-en une).")
            return
        source = reins_source["eleve"]
        # Nouvelle inscription ou reinscription : l'ecriture date d'aujourd'hui,
        # elle doit tomber dans l'annee scolaire active.
        if not eleve and refuser_si_hors_annee(
                dlg, datetime.date.today().isoformat(),
                "La date d'inscription (aujourd'hui)"):
            return
        sexe = dlg.combo_sexe.currentText().split(":")[-1].strip()
        data = {
            "nom": nom, "prenom": prenom, "sexe": sexe,
            "date_naissance": dlg.date_naissance.date().toString("yyyy-MM-dd"),
            "lieu_naissance": dlg.input_lieu_naiss.text().strip(),
            "classe_id": classe_id,
            "ecole_provenance": dlg.input_ecole_provenance.text().strip(),
            "pere_nom": dlg.input_pere_nom.text().strip(),
            "pere_tel": dlg.input_pere_tel.text().strip(),
            "mere_nom": dlg.input_mere_nom.text().strip(),
            "mere_tel": dlg.input_mere_tel.text().strip(),
            "tuteur_nom": dlg.input_tuteur_nom.text().strip(),
            "tuteur_tel": dlg.input_tuteur_tel.text().strip(),
            "adresse": dlg.input_adresse_famille.text().strip(),
            "check_acte": 1 if dlg.check_acte.isChecked() else 0,
            "check_photos": 1 if dlg.check_photos.isChecked() else 0,
            "check_bulletin": 1 if dlg.check_bulletin.isChecked() else 0,
        }
        # Statut : la reinscription est explicite ; sinon on preserve le
        # statut existant en edition, ou on applique le choix en creation.
        if source:
            data["statut"] = "Inscrit"
            # Reinscription ne veut PAS dire redoublement : on preserve le
            # flag existant (seul un avis pedagogique le change).
            data["redoublant"] = source.get("redoublant", 0)
            data["matricule"] = source["matricule"]
        elif eleve:
            data["statut"] = ("Inscrit" if dlg.radio_reins.isChecked()
                              and eleve["statut"] != "Inscrit"
                              else eleve["statut"])
            data["redoublant"] = eleve["redoublant"]
            data["matricule"] = eleve["matricule"]
        else:
            data["statut"] = "Inscrit" if dlg.radio_reins.isChecked() else "Pre-inscrit"
            data["redoublant"] = 0
            data["matricule"] = repos.next_matricule()

        # Photo : enregistree seulement si choisie/retiree pendant la fiche
        if photo_state["modifiee"]:
            if photo_state.get("source"):
                try:
                    data["photo"] = photos.sauvegarder_photo(
                        photo_state["source"], data["matricule"])
                except ValueError as e:
                    QMessageBox.warning(dlg, "Photo", str(e))
                    data["photo"] = photo_state["nom"] or ""
            else:
                data["photo"] = ""  # photo retiree
        else:
            data["photo"] = photo_state["nom"] or ""

        def _encaisser_si_montant(matricule):
            montant = _parse_money(dlg.input_montant_verse.text())
            if not montant or montant <= 0:
                return
            mode = dlg.combo_mode_reglement.currentText().split(":")[-1].strip()
            reference = repos.add_transaction(
                "entree", montant, "Droits de scolarite - inscription",
                "Inscription", f"{prenom} {nom}",
                mode if mode and mode != "Especes" else "Especes")
            from ui.pages.helpers import confirmer
            if confirmer(
                    dlg,
                    f"{fmt_money(montant)} encaisse.\nImprimer le recu ?",
                    "Inscription"):
                try:
                    pdf_export.recu_paiement_pdf(
                        {"prenom": prenom, "nom": nom, "matricule": matricule},
                        montant, mode, reference)
                except RuntimeError as e:
                    QMessageBox.warning(dlg, "Recu", str(e))

        if eleve:
            repos.update_eleve(eleve["id"], data)
            toast.succes(dlg, f"Dossier de {prenom} {nom} mis a jour.")
        elif source:
            # Reinscription : mise a jour du dossier EXISTANT (pas de doublon)
            repos.update_eleve(source["id"], data)
            _encaisser_si_montant(source["matricule"])
            toast.succes(dlg,
                         f"{prenom} {nom} reinscrit. Matricule : {source['matricule']}")
        else:
            new_id = repos.add_eleve(data)
            _encaisser_si_montant(data["matricule"])
            if not (dlg.input_montant_verse.text() or "").strip() or \
                    _parse_money(dlg.input_montant_verse.text()) <= 0:
                toast.succes(dlg, f"Eleve inscrit. Matricule : {data['matricule']}")
        dlg.accept()

    dlg.btn_save.clicked.connect(save)
    dlg.btn_cancel.clicked.connect(dlg.reject)
    _adapter_hauteur(dlg)
    dlg.exec_()
