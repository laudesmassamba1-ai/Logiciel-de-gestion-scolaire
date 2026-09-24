import datetime
from functools import partial
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QLabel as QLbl, QLineEdit, QListWidget, QMessageBox, QPushButton,
    QVBoxLayout, QWidget, QSplitter, QSpacerItem, QGroupBox, QSpinBox,
    QScrollArea, QFileDialog, QTabWidget, QComboBox,
)
from PyQt5.QtGui import QPixmap, QFont

from repositories import repos
from ui import toast
from ui.loader import apply_ui
from ui.pages.helpers import (
    _btn, _simple_btn_style, _styler_carte, confirmer,
)
from core.config import (
    STYLE_BTN_PRIMARY, STYLE_BTN_DANGER, STYLE_BTN_SECONDARY,
    STYLE_GROUP_BOX, STYLE_HELP_MUTED, STYLE_LABEL_BOLD_MUTED,
    STYLE_IMAGE_PLACEHOLDER, STYLE_LIST_CARD, STYLE_BTN_MINI_DANGER,
    STYLE_BTN_ADD_SMALL,
    C_WARN_BG, C_WARN_TEXT,
    C_PRIMARY_PRESSED, C_TEXT,
    C_RED_BG, C_RED, C_RED_BORDER,
    C_AURORA, C_GREEN,
    C_BORDER,
    API_BASE_URL, est_hote, code_ecole,
)
from core import network
from api.client import api_disponible
from services.sync_service import pull_structure
from services.serveur_local import port_configure, adresse_locale
from ui.assistant_serveur import ouvrir_assistant
from services.appreciations import lire_config, enregistrer_config
from services.backup import backup_database, restore_database, list_backups, delete_backup
from ui.workers import run_async


def parametres(page, ctx):
    if not ctx.can_edit("parametres"):
        refuse = QLabel("Acces reserve au directeur : seul le directeur peut "
                      "modifier les parametres de l'etablissement.")
        refuse.setStyleSheet(f"color: {C_RED}; font-size: 14px; padding: 30px;")
        refuse.setWordWrap(True)
        refuse.setAlignment(Qt.AlignCenter)
        lay_refus = QVBoxLayout(page)
        lay_refus.addWidget(refuse)
        return
    apply_ui("parametres/parametres.ui", page)
    page.setStyleSheet(C_AURORA)
    for _card in ("card_inputs", "card1", "card2", "card3", "previewCard"):
        _carte = getattr(page, _card, None)
        if _carte is not None:
            _styler_carte(_carte)

    page.btn_delete.setStyleSheet(STYLE_BTN_DANGER)
    page.btn_update.setStyleSheet(STYLE_BTN_PRIMARY)

    body = page.horizontalLayout_Body
    split = QSplitter(Qt.Horizontal)
    split.setObjectName("parametresSplit")
    split.setHandleWidth(6)
    split.setChildrenCollapsible(False)
    body.removeWidget(page.scrollArea)
    body.removeWidget(page.previewCard)
    split.addWidget(page.scrollArea)
    split.addWidget(page.previewCard)
    split.setStretchFactor(0, 1)
    split.setStretchFactor(1, 0)
    split.setSizes([860, 300])
    body.insertWidget(0, split, 1)

    scroll_lay = page.verticalLayout_Scroll

    def _enlever_stretch_final():
        while scroll_lay.count():
            dernier = scroll_lay.itemAt(scroll_lay.count() - 1)
            if isinstance(dernier, QSpacerItem) and getattr(
                    dernier, "stretch", lambda: 0)() > 0:
                scroll_lay.removeItem(dernier)
            else:
                break

    def _ajouter_au_scroll(widget):
        _enlever_stretch_final()
        scroll_lay.addWidget(widget)
        scroll_lay.addStretch(1)


    backup_group = QGroupBox("Sauvegarde & Restauration")
    backup_group.setStyleSheet(STYLE_GROUP_BOX)
    backup_lay = QVBoxLayout(backup_group)
    backup_lay.setContentsMargins(10, 10, 10, 10)
    backup_lay.setSpacing(8)

    btn_row = QHBoxLayout()
    page.btn_backup = QPushButton("Creer une sauvegarde")
    page.btn_backup.setCursor(Qt.PointingHandCursor)
    page.btn_backup.setStyleSheet(STYLE_BTN_PRIMARY)
    page.btn_restore = QPushButton("Restaurer une sauvegarde")
    page.btn_restore.setCursor(Qt.PointingHandCursor)
    page.btn_restore.setStyleSheet(_simple_btn_style(bg=C_WARN_BG, fg=C_WARN_TEXT, border=C_BORDER))
    page.btn_delete_backup = QPushButton("Supprimer")
    page.btn_delete_backup.setCursor(Qt.PointingHandCursor)
    page.btn_delete_backup.setStyleSheet(_simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER))
    btn_row.addWidget(page.btn_backup)
    btn_row.addWidget(page.btn_restore)
    btn_row.addWidget(page.btn_delete_backup)
    btn_row.addStretch(1)
    backup_lay.addLayout(btn_row)

    page.list_backups = QListWidget()
    page.list_backups.setMaximumHeight(96)
    page.list_backups.setStyleSheet(STYLE_LIST_CARD)
    backup_lay.addWidget(page.list_backups)

    page.lbl_backups_empty = QLbl("Aucune sauvegarde disponible")
    page.lbl_backups_empty.setStyleSheet(STYLE_HELP_MUTED)
    page.lbl_backups_empty.setAlignment(Qt.AlignCenter)
    backup_lay.addWidget(page.lbl_backups_empty)

    _ajouter_au_scroll(backup_group)

    sync_group = QGroupBox("Synchronisation serveur")
    sync_group.setStyleSheet(STYLE_GROUP_BOX)
    sync_lay = QVBoxLayout(sync_group)
    sync_lay.setContentsMargins(10, 10, 10, 10)
    sync_lay.setSpacing(8)
    lbl_sync = QLbl("Rapatrie du serveur la structure de l'ecole modifiee par "
                    "le directeur : cycles, classes, matieres, annees "
                    "scolaires et tarifs. La recuperation se fait aussi "
                    "automatiquement toutes les minutes quand le serveur "
                    "est joignable.")
    lbl_sync.setStyleSheet(STYLE_HELP_MUTED)
    lbl_sync.setWordWrap(True)
    btn_sync = QPushButton("Recuperer maintenant depuis le serveur")
    btn_sync.setCursor(Qt.PointingHandCursor)
    btn_sync.setStyleSheet(STYLE_BTN_SECONDARY)
    row_sync = QHBoxLayout()
    row_sync.addWidget(btn_sync)
    row_sync.addStretch(1)
    sync_lay.addWidget(lbl_sync)
    sync_lay.addLayout(row_sync)
    _ajouter_au_scroll(sync_group)

    def do_sync():
        if not api_disponible(force=True):
            boite = QMessageBox(QMessageBox.Warning, "Serveur non demarre",
                                f"Aucun serveur joignable sur {API_BASE_URL}.\n\n"
                                "Voulez-vous ouvrir l'assistant graphique ?\n"
                                "Il demarre le serveur de l'ecole en un clic,\n"
                                "sans aucune manipulation technique.",
                                QMessageBox.Yes | QMessageBox.No, page)
            if boite.exec_() == QMessageBox.Yes:
                ouvrir_assistant(page)
            return
        btn_sync.setEnabled(False)
        btn_sync.setText("Recuperation en cours...")
        try:
            res = pull_structure()
        except Exception as e:
            QMessageBox.critical(page, "Synchronisation",
                                 f"Echec de la synchronisation :\n{e}")
            return
        finally:
            btn_sync.setEnabled(True)
            btn_sync.setText("Recuperer maintenant depuis le serveur")
        if res.get("erreurs"):
            QMessageBox.warning(
                page, "Synchronisation",
                "Terminee avec des erreurs (serveur injoignable pour "
                "certaines sections ?) :\n" + "\n".join(res["erreurs"]))
            return
        QMessageBox.information(
            page, "Synchronisation",
            f"Donnees recuperees du serveur :\n"
            f"- Cycles : {res['cycles']}\n"
            f"- Classes : {res['classes']}\n"
            f"- Matieres : {res['matieres']}\n"
            f"- Annees scolaires : {res['annees']}\n"
            f"- Tarifs : {res['tarifs']}\n\n"
            "Ces donnees s'appliquent desormais a tous les postes.")

    btn_sync.clicked.connect(do_sync)

    # ── Reseau & connexion entre les postes ──────────────────────────
    reseau_group = QGroupBox("Reseau & connexion entre les postes")
    reseau_group.setStyleSheet(STYLE_GROUP_BOX)
    reseau_lay = QVBoxLayout(reseau_group)
    reseau_lay.setContentsMargins(10, 10, 10, 10)
    reseau_lay.setSpacing(8)

    lbl_reseau_help = QLbl(
        "La connexion entre les postes est AUTOMATIQUE : des qu'un autre "
        "ordinateur de l'ecole est joignable (WiFi de l'ecole, Ethernet ou "
        "Internet), il rejoint le serveur tout seul. Vous pouvez aussi "
        "reprendre la main et tout configurer a la main dans la fenetre "
        "de configuration (adresse, port, reseau WiFi de l'ecole, code de "
        "l'ecole, hotspot, demarrage automatique).")
    lbl_reseau_help.setStyleSheet(STYLE_HELP_MUTED)
    lbl_reseau_help.setWordWrap(True)
    reseau_lay.addWidget(lbl_reseau_help)

    lbl_reseau_statut = QLbl()
    lbl_reseau_statut.setWordWrap(True)
    reseau_lay.addWidget(lbl_reseau_statut)

    lbl_reseau_code = QLbl()
    lbl_reseau_code.setStyleSheet(STYLE_HELP_MUTED)
    reseau_lay.addWidget(lbl_reseau_code)

    btn_reseau = QPushButton("Ouvrir la configuration reseau (manuel)")
    btn_reseau.setCursor(Qt.PointingHandCursor)
    btn_reseau.setStyleSheet(STYLE_BTN_SECONDARY)
    reseau_lay.addWidget(btn_reseau)

    _ajouter_au_scroll(reseau_group)

    def _refresh_reseau(verifier_en_ligne=True):
        actif = network.sync_active()
        hote = est_hote()
        debut = ("Sur ce poste : SERVEUR de l'ecole (hote) — "
                 if hote else "Sur ce poste : CLIENT raccorde a - ") + API_BASE_URL
        if actif:
            lbl_reseau_statut.setStyleSheet(
                f"color: {C_PRIMARY_PRESSED};"
                " font-size: 13px; font-weight: 800;")
            lbl_reseau_statut.setText(debut + " — verification de la liaison...")
        else:
            lbl_reseau_statut.setStyleSheet(
                f"color: {C_TEXT}; font-size: 13px; font-weight: 800;")
            lbl_reseau_statut.setText(
                "Mode AUTONOME — les donnees restent sur cet ordinateur "
                "uniquement.")
        code = code_ecole()
        lbl_reseau_code.setText(
            f"Code de l'ecole : {code or 'aucun'}"
            + (f"   |   Adresse pour les autres postes : "
               f"{_adresse_locale()}" if hote else ""))
        btn_reseau.setText("Ouvrir la configuration reseau (manuel)")
        btn_reseau.setEnabled(True)
        if not (actif and verifier_en_ligne):
            return

        def _tache():
            try:
                return api_disponible(force=True)
            except Exception:
                return False

        def _fini(en_ligne):
            if not network.sync_active():
                return
            lbl_reseau_statut.setText(
                debut + (" — en ligne."
                         if en_ligne else " — serveur injoignable pour l'instant."))
            lbl_reseau_statut.setStyleSheet(
                f"color: {C_GREEN if en_ligne else C_RED};"
                " font-size: 13px; font-weight: 800;")

        run_async(_tache, _fini)

    def _adresse_locale():
        return adresse_locale(port_configure())

    def ouvrir_reseau():
        btn_reseau.setEnabled(False)
        try:
            ouvrir_assistant(page)
        finally:
            _refresh_reseau()

    btn_reseau.clicked.connect(ouvrir_reseau)
    _refresh_reseau()

    img_lay = QHBoxLayout()
    for key, label_text in [("bandeau_haut", "Bandeau haut"), ("bandeau_bas", "Bandeau bas"), ("signature", "Signature")]:
        box = QVBoxLayout()
        lbl_title = QLbl(label_text)
        lbl_title.setStyleSheet(STYLE_LABEL_BOLD_MUTED)
        lbl_title.setAlignment(Qt.AlignCenter)
        img_lbl = QLbl()
        img_lbl.setObjectName(f"lbl_image_{key}")
        img_lbl.setFixedSize(190, 72)
        img_lbl.setStyleSheet(STYLE_IMAGE_PLACEHOLDER)
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setText("Aucune image")
        setattr(page, f"lbl_image_{key}", img_lbl)
        box.addWidget(lbl_title)
        box.addWidget(img_lbl)
        img_lay.addLayout(box)

    img_host = QWidget()
    img_host.setLayout(img_lay)
    _ajouter_au_scroll(img_host)

    # ── Emplacement des emblemes dans les documents PDF ────────────────
    # Alignement horizontal + hauteur max pour chaque embleme ; stockes
    # dans la table parametres ({key}_align / {key}_hauteur) et appliques
    # par services/pdf_export._entete_doc.
    EMBLEMES = [
        ("bandeau_haut", "Bandeau haut", "centre", 80),
        ("bandeau_bas", "Bandeau bas", "centre", 80),
        ("signature", "Signature", "droite", 50),
    ]
    _defauts_emblemes = {key: (align, haut)
                         for key, _lbl, align, haut in EMBLEMES}
    embleme_widgets = {}
    embleme_group = QGroupBox("Emplacement des emblemes (documents PDF)")
    embleme_group.setStyleSheet(STYLE_GROUP_BOX)
    embleme_lay = QVBoxLayout(embleme_group)
    embleme_lay.setContentsMargins(10, 10, 10, 10)
    embleme_lay.setSpacing(8)
    lbl_embleme_help = QLbl(
        "Position et taille de chaque image dans l'entete des PDF generes "
        "(bulletins, recus, certificats, rapports).")
    lbl_embleme_help.setStyleSheet(STYLE_HELP_MUTED)
    lbl_embleme_help.setWordWrap(True)
    embleme_lay.addWidget(lbl_embleme_help)
    for key, label_text, align_defaut, haut_defaut in EMBLEMES:
        row = QHBoxLayout()
        lbl_em = QLbl(label_text)
        lbl_em.setStyleSheet(STYLE_LABEL_BOLD_MUTED)
        lbl_em.setFixedWidth(150)
        combo_align = QComboBox()
        combo_align.addItems(["centre", "gauche", "droite"])
        combo_align.setCurrentText(align_defaut)
        spin_haut = QSpinBox()
        spin_haut.setRange(30, 400)
        spin_haut.setValue(haut_defaut)
        spin_haut.setSuffix(" px")
        row.addWidget(lbl_em)
        row.addWidget(QLbl("Alignement :"))
        row.addWidget(combo_align)
        row.addSpacing(16)
        row.addWidget(QLbl("Hauteur max :"))
        row.addWidget(spin_haut)
        row.addStretch(1)
        embleme_lay.addLayout(row)
        embleme_widgets[key] = (combo_align, spin_haut)
    _ajouter_au_scroll(embleme_group)

    images = {"bandeau_haut": None, "bandeau_bas": None, "signature": None}
    upload_map = {"bandeau_haut": page.btn_upload1,
                  "bandeau_bas": page.btn_upload2,
                  "signature": page.btn_upload3}

    def load():
        params = repos.parametres()
        page.input_nom_ecole.setText(params.get("nom_ecole", ""))
        page.input_signer_name.setText(params.get("signataire_nom", ""))
        page.input_signer_title.setText(params.get("signataire_titre", ""))
        page.input_city.setText(params.get("ville", ""))
        page.input_country.setText(params.get("pays", ""))
        cles_config = ("nom_ecole", "signataire_nom", "signataire_titre", "ville",
                       "pays", "bandeau_haut", "bandeau_bas", "signature")
        remplis = sum(1 for cle in cles_config if params.get(cle))
        page.lbl_progression.setText(
            f"Configuration : {round(remplis / len(cles_config) * 100)}%")
        _display_images(params)
        for key, (combo, spin) in embleme_widgets.items():
            align_def, haut_def = _defauts_emblemes[key]
            val_align = str(params.get(f"{key}_align", "") or "")
            combo.setCurrentText(val_align if val_align in (
                "gauche", "centre", "droite") else align_def)
            try:
                spin.setValue(int(params.get(f"{key}_hauteur", "") or haut_def))
            except (TypeError, ValueError):
                spin.setValue(haut_def)
        _load_appreciations()

    def _display_images(params):
        img_data = {
            "bandeau_haut": getattr(page, "lbl_image_bandeau_haut", None),
            "bandeau_bas": getattr(page, "lbl_image_bandeau_bas", None),
            "signature": getattr(page, "lbl_image_signature", None),
        }
        for key, lbl in img_data.items():
            if lbl is None:
                continue
            img_path = params.get(key, "")
            if img_path and Path(img_path).exists():
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    lbl.setPixmap(pixmap.scaled(190, 75, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    continue
                lbl.setText("Aucune image")

    def upload(key):
        path, _ = QFileDialog.getOpenFileName(
            page, "Choisir une image", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        # Validation : extension reconnue + taille raisonnable (5 Mo max),
        # sinon un fichier geant pouvait etre copie sans controle.
        if not path.lower().endswith((".png", ".jpg", ".jpeg")):
            QMessageBox.warning(page, "Image",
                                "Formats acceptes : PNG, JPG, JPEG.")
            return
        if Path(path).stat().st_size > 5 * 1024 * 1024:
            QMessageBox.warning(page, "Image",
                                "Image trop volumineuse (maximum 5 Mo).")
            return
        images[key] = path
        lbl = getattr(page, f"lbl_image_{key}", None)
        if lbl is not None:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                lbl.setPixmap(pixmap.scaled(190, 75, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        page.lbl_status.setText(f"{key} choisi : {Path(path).name}")

    for key, btn in upload_map.items():
        btn.clicked.connect(partial(upload, key))

    # ── Appreciations configurables ──────────────────────────────────
    app_group = QGroupBox("Appreciations (notes)")
    app_group.setStyleSheet(STYLE_GROUP_BOX)
    app_lay = QVBoxLayout(app_group)
    app_lay.setContentsMargins(10, 10, 10, 10)
    app_lay.setSpacing(8)
    lbl_app_help = QLbl("Configurez les seuils et libelles des appreciations affichees pour les notes.")
    lbl_app_help.setStyleSheet(STYLE_HELP_MUTED)
    lbl_app_help.setWordWrap(True)
    app_lay.addWidget(lbl_app_help)

    app_rows_layout = QVBoxLayout()
    app_lay.addLayout(app_rows_layout)

    app_row_widgets = []  # [(spin_seuil, input_libelle)]

    def _ajouter_ligne_app(seuil=0, libelle=""):
        row = QHBoxLayout()
        spin = QSpinBox()
        spin.setRange(0, 20)
        spin.setValue(seuil)
        spin.setFixedWidth(90)
        lbl_seuil = QLbl("/20  →")
        lbl_seuil.setStyleSheet(STYLE_HELP_MUTED)
        inp = QLineEdit(libelle)
        inp.setPlaceholderText("Nom de l'appreciation")
        btn_suppr = QPushButton("✕")
        btn_suppr.setCursor(Qt.PointingHandCursor)
        btn_suppr.setFixedSize(26, 26)
        btn_suppr.setStyleSheet(STYLE_BTN_MINI_DANGER)
        row.addWidget(spin)
        row.addWidget(lbl_seuil)
        row.addWidget(inp, 1)
        row.addWidget(btn_suppr)
        app_rows_layout.addLayout(row)
        app_row_widgets.append((spin, inp))
        btn_suppr.clicked.connect(lambda: _supprimer_ligne_app(row, (spin, inp)))

    def _supprimer_ligne_app(row_layout, widgets):
        if len(app_row_widgets) <= 1:
            return
        app_row_widgets.remove(widgets)
        while row_layout.count():
            item = row_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    btn_ajouter_app = QPushButton("+ Ajouter un palier")
    btn_ajouter_app.setCursor(Qt.PointingHandCursor)
    btn_ajouter_app.setStyleSheet(STYLE_BTN_ADD_SMALL)
    btn_ajouter_app.clicked.connect(lambda: _ajouter_ligne_app())
    app_lay.addWidget(btn_ajouter_app)

    _ajouter_au_scroll(app_group)

    def _load_appreciations():
        while app_rows_layout.count():
            item = app_rows_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        app_row_widgets.clear()
        config = lire_config()
        for p in config:
            _ajouter_ligne_app(p["seuil"], p["libelle"])

    def _save_appreciations():
        paliers = []
        for spin, inp in app_row_widgets:
            paliers.append({"seuil": spin.value(), "libelle": inp.text().strip()})
        enregistrer_config(paliers)

    def save():
        repos.set_parametre("nom_ecole", page.input_nom_ecole.text().strip())
        repos.set_parametre("signataire_nom", page.input_signer_name.text().strip())
        repos.set_parametre("signataire_titre", page.input_signer_title.text().strip())
        repos.set_parametre("ville", page.input_city.text().strip())
        repos.set_parametre("pays", page.input_country.text().strip())
        for key, path in images.items():
            if path:
                import shutil
                from core.config import DOCS_DIR
                DOCS_DIR.mkdir(parents=True, exist_ok=True)
                dest = DOCS_DIR / f"{key}_{datetime.date.today():%Y%m%d}{Path(path).suffix}"
                shutil.copy2(path, dest)
                repos.set_parametre(key, str(dest))
        for key, (combo, spin) in embleme_widgets.items():
            repos.set_parametre(f"{key}_align", combo.currentText())
            repos.set_parametre(f"{key}_hauteur", str(spin.value()))
        page.lbl_status.setText("Configuration mise a jour.")
        _save_appreciations()
        toast.succes(page, "Configuration enregistree.")
        load()

    def delete_config():
        if confirmer(page, "Supprimer la configuration ?", "Parametres"):
            repos.delete_parametres()
            load()
            page.lbl_status.setText("Configuration supprimee.")

    def do_backup():
        try:
            path = backup_database()
            toast.succes(page, f"Sauvegarde creee avec succes :\n{path}")
            _refresh_backups()
        except Exception as e:
            QMessageBox.critical(page, "Erreur", f"Echec de la sauvegarde :\n{e}")

    def do_restore():
        path, _ = QFileDialog.getOpenFileName(
            page, "Restaurer une sauvegarde", "", "Fichiers DB (*.db)")
        if not path:
            return
        if confirmer(page, "Restaurer cette sauvegarde ?\n"
                      "L'application redemarrera.", "Restauration"):
            try:
                restore_database(path)
                QMessageBox.information(page, "Restauration",
                                        "Base restauree. L'application va redemarrer.")
                import os, sys
                os.execl(sys.executable, sys.executable, *sys.argv)
            except Exception as e:
                QMessageBox.critical(page, "Erreur",
                                     f"Echec de la restauration :\n{e}")

    def _refresh_backups():
        backups = list_backups()
        page.list_backups.clear()
        for b in backups:
            page.list_backups.addItem(
                f"{b['name']}  |  {b['size_mb']} Mo  |  {b['date']}")
        page.lbl_backups_empty.setVisible(not backups)

    def do_delete_backup():
        item = page.list_backups.currentItem()
        if not item:
            QMessageBox.information(page, "Sauvegarde", "Selectionnez une sauvegarde a supprimer.")
            return
        backups = list_backups()
        idx = page.list_backups.row(item)
        if 0 <= idx < len(backups):
            if confirmer(page,
                         f"Supprimer la sauvegarde {backups[idx]['name']} ?",
                         "Supprimer"):
                delete_backup(backups[idx]["path"])
                _refresh_backups()

    page.btn_update.clicked.connect(save)
    page.btn_delete.clicked.connect(delete_config)
    page.btn_backup.clicked.connect(do_backup)
    page.btn_restore.clicked.connect(do_restore)
    page.btn_delete_backup.clicked.connect(do_delete_backup)

    # ── Passage du contenu du scroll en onglets (sans casser les liens) ──
    def _regrouper_onglets(scroll_lay):
        page.backup_group = backup_group
        page.sync_group = sync_group
        page.reseau_group = reseau_group
        page.image_host = img_host
        page.appreciations_group = app_group

        def _appartenance(w):
            nom = w.objectName() or ""
            if nom in ("card_inputs", "card1", "card2", "card3",
                       "image_host"):
                return (0, "Etablissement")
            if nom == "appreciations_group":
                return (1, "Appreciations")
            if nom in ("backup_group", "sync_group", "reseau_group"):
                return (2, "Systeme")
            return None

        contenus = []
        non_classes = []
        backup_group.setObjectName("backup_group")
        sync_group.setObjectName("sync_group")
        reseau_group.setObjectName("reseau_group")
        img_host.setObjectName("image_host")
        app_group.setObjectName("appreciations_group")
        while scroll_lay.count():
            item = scroll_lay.takeAt(0)
            w = item.widget()
            if w is None:
                continue
            groupe = _appartenance(w)
            if groupe is None:
                non_classes.append(w)
            else:
                contenus.append((groupe[0], groupe[1], w))

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setStyleSheet(
            "QTabBar::tab { padding: 8px 16px; font-weight: 600; }"
            "QTabWidget::pane { border: none; }"
            "QTabWidget#ongletsParams { background: transparent; }")
        tabs.setObjectName("ongletsParams")

        pages = {}
        for indice, nom_onglet, w in sorted(contenus,
                                            key=lambda x: x[0]):
            if nom_onglet not in pages:
                page_tab = QWidget()
                lay_tab = QVBoxLayout(page_tab)
                lay_tab.setContentsMargins(0, 8, 0, 8)
                lay_tab.setSpacing(8)
                pages[nom_onglet] = (page_tab, lay_tab)
            _, lay_tab = pages[nom_onglet]
            lay_tab.addWidget(w)
            lay_tab.addStretch(1)

        for nom_onglet in ("Etablissement", "Appreciations", "Systeme"):
            conteneur = pages.get(nom_onglet)
            if conteneur is not None:
                tabs.addTab(conteneur[0], nom_onglet)

        if tabs.count() == 0:
            for w in non_classes:
                scroll_lay.addWidget(w)
            return
        for w in non_classes:
            scroll_lay.addWidget(w)
        scroll_lay.addWidget(tabs)

    _regrouper_onglets(scroll_lay)

    load()
    _refresh_backups()
    page.refresh = lambda: (load(), _refresh_backups(), _refresh_reseau())
