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
        page.lbl_progression.setText("Progression de la configuration: 100%")
        _display_images(params)

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
        if path:
            images[key] = path
            page.lbl_status.setText(f"{key} choisi : {Path(path).name}")

    for key, btn in upload_map.items():
        btn.clicked.connect(partial(upload, key))

    def save():
        repos.set_parametre("signataire_nom", page.input_signer_name.text().strip())
        repos.set_parametre("signataire_titre", page.input_signer_title.text().strip())
        repos.set_parametre("ville", page.input_city.text().strip())
        repos.set_parametre("pays", page.input_country.text().strip())
        for key, path in images.items():
            if path:
                import shutil
                from core.config import DOCS_DIR
                dest = DOCS_DIR / f"{key}_{datetime.date.today():%Y%m%d}{Path(path).suffix}"
                shutil.copy2(path, dest)
                repos.set_parametre(key, str(dest))
        page.lbl_status.setText("Configuration mise a jour.")
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
    page.refresh = load
