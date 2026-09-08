import datetime
from functools import partial
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from repositories import repos
from ui.loader import apply_ui
from ui.pages.helpers import (
    _btn, _simple_btn_style,
)
from core.config import STYLE_BTN_PRIMARY, C_TEXT, C_BORDER, C_GOLD, C_GOLD_BG, C_GOLD_PRESSED, C_GOLD_BORDER, C_RED, C_RED_BG, C_RED_BORDER, C_TEXT_MUTED, C_BG_ALT


def parametres(page, ctx):
    if page.layout() is not None:
        return
    if not ctx.can_edit("parametres"):
        from PyQt5.QtWidgets import QLabel as _Lbl
        refuse = _Lbl("Acces reserve au directeur : seul le directeur peut "
                      "modifier les parametres de l'etablissement.")
        refuse.setStyleSheet("color: #B91C1C; font-size: 14px; padding: 30px;")
        refuse.setWordWrap(True)
        refuse.setAlignment(Qt.AlignCenter)
        lay_refus = QVBoxLayout(page)
        lay_refus.addWidget(refuse)
        return
    apply_ui("parametres/parametres.ui", page)

    from PyQt5.QtWidgets import QGroupBox, QListWidget, QLabel as QLbl
    from PyQt5.QtGui import QPixmap
    from PyQt5.QtCore import Qt as QtConst

    backup_group = QGroupBox("Sauvegarde & Restauration")
    backup_group.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {C_TEXT}; border: 1px solid {C_BORDER}; border-radius: 8px; padding: 12px; margin-top: 8px; }}")
    backup_lay = QVBoxLayout(backup_group)

    btn_row = QHBoxLayout()
    page.btn_backup = QPushButton("Creer une sauvegarde")
    page.btn_backup.setCursor(Qt.PointingHandCursor)
    page.btn_backup.setStyleSheet(STYLE_BTN_PRIMARY)
    page.btn_restore = QPushButton("Restaurer une sauvegarde")
    page.btn_restore.setCursor(Qt.PointingHandCursor)
    page.btn_restore.setStyleSheet(_simple_btn_style(bg=C_GOLD_BG, fg=C_GOLD_PRESSED, border=C_GOLD_BORDER))
    page.btn_delete_backup = QPushButton("Supprimer")
    page.btn_delete_backup.setCursor(Qt.PointingHandCursor)
    page.btn_delete_backup.setStyleSheet(_simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER))
    btn_row.addWidget(page.btn_backup)
    btn_row.addWidget(page.btn_restore)
    btn_row.addWidget(page.btn_delete_backup)
    btn_row.addStretch(1)
    backup_lay.addLayout(btn_row)

    page.list_backups = QListWidget()
    page.list_backups.setMaximumHeight(120)
    page.list_backups.setStyleSheet(f"QListWidget {{ border: 1px solid {C_BORDER}; border-radius: 6px; background: {C_BG_ALT}; }}")
    backup_lay.addWidget(page.list_backups)

    page.lbl_backups_empty = QLbl("Aucune sauvegarde disponible")
    page.lbl_backups_empty.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px;")
    page.lbl_backups_empty.setAlignment(Qt.AlignCenter)
    backup_lay.addWidget(page.lbl_backups_empty)

    page.verticalLayout.addWidget(backup_group)

    sync_group = QGroupBox("Synchronisation serveur")
    sync_group.setStyleSheet(backup_group.styleSheet())
    sync_lay = QVBoxLayout(sync_group)
    lbl_sync = QLbl("Rapatrie du serveur la structure de l'ecole modifiee par "
                    "le directeur : cycles, classes, matieres, annees "
                    "scolaires et tarifs. La recuperation se fait aussi "
                    "automatiquement toutes les minutes quand le serveur "
                    "est joignable.")
    lbl_sync.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px;")
    lbl_sync.setWordWrap(True)
    btn_sync = QPushButton("Recuperer maintenant depuis le serveur")
    btn_sync.setCursor(Qt.PointingHandCursor)
    btn_sync.setStyleSheet(STYLE_BTN_PRIMARY)
    row_sync = QHBoxLayout()
    row_sync.addWidget(btn_sync)
    row_sync.addStretch(1)
    sync_lay.addWidget(lbl_sync)
    sync_lay.addLayout(row_sync)
    page.verticalLayout.addWidget(sync_group)

    def do_sync():
        from api.client import api_disponible
        from core import network
        from core.config import API_BASE_URL
        if not api_disponible(force=True):
            boite = QMessageBox(QMessageBox.Warning, "Serveur non demarre",
                                f"Aucun serveur joignable sur {API_BASE_URL}.\n\n"
                                "Voulez-vous ouvrir l'assistant graphique ?\n"
                                "Il demarre le serveur de l'ecole en un clic,\n"
                                "sans aucune manipulation technique.",
                                QMessageBox.Yes | QMessageBox.No, page)
            if boite.exec_() == QMessageBox.Yes:
                from ui.assistant_serveur import ouvrir_assistant
                ouvrir_assistant(page)
            return
        from services.sync_service import pull_structure
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

    img_lay = QHBoxLayout()
    for key, label_text in [("bandeau_haut", "Bandeau haut"), ("bandeau_bas", "Bandeau bas"), ("signature", "Signature")]:
        box = QVBoxLayout()
        lbl_title = QLbl(label_text)
        lbl_title.setStyleSheet(f"font-weight: bold; color: {C_TEXT_MUTED}; font-size: 11px; border: none;")
        lbl_title.setAlignment(Qt.AlignCenter)
        img_lbl = QLbl()
        img_lbl.setObjectName(f"lbl_image_{key}")
        img_lbl.setFixedSize(200, 80)
        img_lbl.setStyleSheet(f"border: 1px dashed {C_BORDER}; border-radius: 6px; background: {C_BG_ALT};")
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setText("Aucune image")
        setattr(page, f"lbl_image_{key}", img_lbl)
        box.addWidget(lbl_title)
        box.addWidget(img_lbl)
        img_lay.addLayout(box)
    page.verticalLayout.addLayout(img_lay)

    images = {"bandeau_haut": None, "bandeau_bas": None, "signature": None}
    upload_map = {"bandeau_haut": page.btn_upload1,
                  "bandeau_bas": page.btn_upload2,
                  "signature": page.btn_upload3}

    def load():
        params = repos.parametres()
        page.input_signer_name.setText(params.get("signataire_nom", ""))
        page.input_signer_title.setText(params.get("signataire_titre", ""))
        page.input_city.setText(params.get("ville", ""))
        page.input_country.setText(params.get("pays", ""))
        remplis = sum(1 for cle in ("signataire_nom", "signataire_titre", "ville", "pays",
                                    "bandeau_haut", "bandeau_bas", "signature")
                      if params.get(cle))
        page.lbl_progression.setText(
            f"Progression de la configuration : {round(remplis / 7 * 100)}%")
        _display_images(params)
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
                    lbl.setPixmap(pixmap.scaled(190, 75, QtConst.KeepAspectRatio, QtConst.SmoothTransformation))
                    continue
            lbl.setText("Aucune image")

    def upload(key):
        from PyQt5.QtWidgets import QFileDialog
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
                lbl.setPixmap(pixmap.scaled(190, 75, QtConst.KeepAspectRatio, QtConst.SmoothTransformation))
        page.lbl_status.setText(f"{key} choisi : {Path(path).name}")

    for key, btn in upload_map.items():
        btn.clicked.connect(partial(upload, key))

    # ── Appreciations configurables ──────────────────────────────────
    from PyQt5.QtWidgets import QSpinBox, QScrollArea
    from PyQt5.QtGui import QFont

    app_group = QGroupBox("Appreciations (notes)")
    app_group.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {C_TEXT}; border: 1px solid {C_BORDER}; border-radius: 8px; padding: 12px; margin-top: 8px; }}")
    app_lay = QVBoxLayout(app_group)
    lbl_app_help = QLbl("Configurez les seuils et libelles des appreciations affichees pour les notes.")
    lbl_app_help.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px;")
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
        spin.setFixedWidth(60)
        spin.setStyleSheet(f"border: 1px solid {C_BORDER}; border-radius: 6px; padding: 4px 8px;")
        lbl_seuil = QLbl("/20  →")
        lbl_seuil.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px; border: none;")
        inp = QLineEdit(libelle)
        inp.setPlaceholderText("Nom de l'appreciation")
        inp.setStyleSheet(f"border: 1px solid {C_BORDER}; border-radius: 6px; padding: 4px 8px;")
        btn_suppr = QPushButton("✕")
        btn_suppr.setFixedSize(26, 26)
        btn_suppr.setStyleSheet(f"background: {C_RED_BG}; color: {C_RED}; border: 1px solid {C_RED_BORDER}; border-radius: 13px; font-size: 12px; font-weight: bold;")
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
    btn_ajouter_app.setStyleSheet(f"background: {C_GOLD_BG}; color: {C_GOLD_PRESSED}; border: 1px solid {C_GOLD_BORDER}; border-radius: 8px; padding: 6px 14px; font-weight: 600; font-size: 12px;")
    btn_ajouter_app.clicked.connect(lambda: _ajouter_ligne_app())
    app_lay.addWidget(btn_ajouter_app)

    page.verticalLayout.addWidget(app_group)

    def _load_appreciations():
        from services.appreciations import lire_config
        for w_data in app_row_widgets:
            pass  # will clear below
        # clear existing rows
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
        from services.appreciations import enregistrer_config
        paliers = []
        for spin, inp in app_row_widgets:
            paliers.append({"seuil": spin.value(), "libelle": inp.text().strip()})
        enregistrer_config(paliers)

    def save():
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
        page.lbl_status.setText("Configuration mise a jour.")
        _save_appreciations()
        QMessageBox.information(page, "Parametres", "Configuration enregistree.")
        load()

    def delete_config():
        if QMessageBox.question(page, "Parametres",
                                "Supprimer la configuration ?") == QMessageBox.Yes:
            repos.delete_parametres()
            load()
            page.lbl_status.setText("Configuration supprimee.")

    def do_backup():
        from services.backup import backup_database
        try:
            path = backup_database()
            QMessageBox.information(page, "Sauvegarde",
                                    f"Sauvegarde creee avec succes :\n{path}")
            _refresh_backups()
        except Exception as e:
            QMessageBox.critical(page, "Erreur", f"Echec de la sauvegarde :\n{e}")

    def do_restore():
        from PyQt5.QtWidgets import QFileDialog
        from services.backup import restore_database
        path, _ = QFileDialog.getOpenFileName(
            page, "Restaurer une sauvegarde", "", "Fichiers DB (*.db)")
        if not path:
            return
        if QMessageBox.question(page, "Restauration",
                                "Restaurer cette sauvegarde ?\n"
                                "L'application redemarrera.") == QMessageBox.Yes:
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
        from services.backup import list_backups
        backups = list_backups()
        page.list_backups.clear()
        for b in backups:
            page.list_backups.addItem(
                f"{b['name']}  |  {b['size_mb']} Mo  |  {b['date']}")
        page.lbl_backups_empty.setVisible(not backups)

    def do_delete_backup():
        from services.backup import delete_backup, list_backups
        item = page.list_backups.currentItem()
        if not item:
            QMessageBox.information(page, "Sauvegarde", "Selectionnez une sauvegarde a supprimer.")
            return
        backups = list_backups()
        idx = page.list_backups.row(item)
        if 0 <= idx < len(backups):
            if QMessageBox.question(page, "Supprimer",
                                    f"Supprimer la sauvegarde {backups[idx]['name']} ?") == QMessageBox.Yes:
                delete_backup(backups[idx]["path"])
                _refresh_backups()

    page.btn_update.clicked.connect(save)
    page.btn_delete.clicked.connect(delete_config)
    page.btn_backup.clicked.connect(do_backup)
    page.btn_restore.clicked.connect(do_restore)
    page.btn_delete_backup.clicked.connect(do_delete_backup)

    load()
    _refresh_backups()
    page.refresh = lambda: (load(), _refresh_backups())
