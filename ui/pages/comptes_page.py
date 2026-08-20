from functools import partial

from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPushButton, QTableWidgetItem, QVBoxLayout, QComboBox,
    QFormLayout, QWidget,
)

from core.config import ROLE_LABELS, C_GOLD, C_GOLD_BG, C_GOLD_PRESSED, C_GOLD_BORDER, C_RED, C_RED_BG, C_RED_BORDER
from database.db import hash_password
from repositories import repos
from services import auth
from ui.loader import apply_ui
from ui.pages.helpers import (
    _btn, _simple_btn_style, _fit_rows,
)


def comptes(page, ctx):
    if page.layout() is not None:
        return
    apply_ui("comptes/comptes.ui", page)
    _fit_rows(page.table_comptes)
    page.combo_filter_role.clear()
    page.combo_filter_role.addItems(["Tous les roles", "Directeur", "Gestionnaire"])

    def refresh():
        role = page.combo_filter_role.currentText()
        recherche = page.input_search_compte.text().strip()
        rows = repos.utilisateurs(role=role, recherche=recherche)
        page.table_comptes.setRowCount(len(rows))
        for i, u in enumerate(rows):
            values = [u["nom_complet"], u["email"] or "-",
                      ROLE_LABELS.get(u["role"], u["role"]),
                      "Actif" if u["actif"] else "Inactif", u["created_at"][:10]]
            for j, val in enumerate(values):
                page.table_comptes.setItem(i, j, QTableWidgetItem(str(val)))
            cell = QWidget()
            lay = QHBoxLayout(cell)
            lay.setContentsMargins(2, 2, 2, 2)
            lay.addWidget(_btn("Activer" if not u["actif"] else "Desactiver",
                               partial(_toggle, page, ctx, u),
                                _simple_btn_style(bg=C_GOLD_BG, fg=C_GOLD, border=C_GOLD_BORDER)))
            lay.addWidget(_btn("Mdp", partial(_reset_pwd, page, ctx, u),
                                _simple_btn_style(bg=C_GOLD_BG, fg=C_GOLD_PRESSED, border=C_GOLD_BORDER)))
            lay.addWidget(_btn("Supprimer", partial(_delete_compte, page, ctx, u),
                                _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)))
            page.table_comptes.setCellWidget(i, 5, cell)
        page.table_comptes.resizeColumnsToContents()
        page.table_comptes.horizontalHeader().setStretchLastSection(True)
        page.table_comptes.horizontalHeader().setMinimumSectionSize(80)
        page.lbl_empty_state_comptes.setVisible(not rows)
        page.table_comptes.setVisible(bool(rows))

        all_rows = repos.utilisateurs()
        actifs = [u for u in all_rows if u["actif"]]
        page.lbl_kpi1_valeur.setText(str(len(actifs)))
        page.lbl_kpi2_valeur.setText(str(len([u for u in actifs if u["role"] == "directeur"])))
        page.lbl_kpi3_valeur.setText(str(len([u for u in actifs if u["role"] == "gestionnaire"])))
        page.lbl_kpi4_valeur.setText(str(len([u for u in all_rows if not u["actif"]])))

    def _toggle(parent, ctx, u):
        repos.toggle_compte(u["id"], not u["actif"])
        refresh()

    def _reset_pwd(parent, ctx, u):
        new_pwd = auth.random_password()
        if QMessageBox.question(parent, "Reinitialisation",
                                f"Reinitialiser le mot de passe de {u['nom_complet']} ?\n"
                                f"Le nouveau mot de passe sera : {new_pwd}") == QMessageBox.Yes:
            repos.reset_password(u["id"], hash_password(new_pwd))
            QMessageBox.information(parent, "Reinitialisation",
                                    f"Nouveau mot de passe : {new_pwd}")

    def _delete_compte(parent, ctx, u):
        if QMessageBox.question(parent, "Supprimer",
                                f"Supprimer le compte de {u['nom_complet']} ?") \
                == QMessageBox.Yes:
            repos.delete_compte(u["id"])
            refresh()

    page.btn_add_compte.clicked.connect(lambda: open_compte_dialog(page, ctx))
    page.btn_apply_filter_compte.clicked.connect(refresh)
    page.input_search_compte.textChanged.connect(refresh)
    page.combo_filter_role.currentIndexChanged.connect(refresh)

    refresh()
    page.refresh = refresh


def open_compte_dialog(parent, ctx, compte=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouveau Compte")
    dlg.resize(440, 520)
    dlg.setMinimumSize(380, 420)
    apply_ui("comptes/compte_dialog.ui", dlg)
    dlg.combo_role_compte.clear()
    dlg.combo_role_compte.addItems(["Directeur", "Gestionnaire"])
    if compte:
        dlg.lbl_dialog_title.setText("Modifier le Compte")
        dlg.input_nom_compte.setText(compte["nom_complet"])
        dlg.input_email_compte.setText(compte["email"] or "")
        dlg.input_telephone_compte.setText(compte["telephone"] or "")
        idx = dlg.combo_role_compte.findText(ROLE_LABELS.get(compte["role"], ""))
        if idx >= 0:
            dlg.combo_role_compte.setCurrentIndex(idx)
        dlg.check_compte_actif.setChecked(bool(compte["actif"]))
        dlg.btn_save.setText("Enregistrer")

    def save():
        nom = dlg.input_nom_compte.text().strip()
        email = dlg.input_email_compte.text().strip()
        if not nom or not email:
            QMessageBox.warning(dlg, "Compte",
                                "Le nom complet et l'email sont obligatoires.")
            return
        role_label = dlg.combo_role_compte.currentText()
        role = {v: k for k, v in ROLE_LABELS.items()}.get(role_label, role_label.lower())
        telephone = dlg.input_telephone_compte.text().strip()
        actif = dlg.check_compte_actif.isChecked()
        if compte:
            repos.update_compte(compte["id"], nom, email, telephone, role, actif)
            QMessageBox.information(dlg, "Compte", "Compte mis a jour.")
        else:
            password = auth.random_password()
            repos.add_compte(nom, email, telephone, role,
                             hash_password(password), actif)
            QMessageBox.information(
                dlg, "Compte",
                f"Compte cree pour {nom}.\nIdentifiant : {email.split('@')[0]}"
                f"\nMot de passe temporaire : {password}")
        dlg.accept()

    dlg.btn_save.clicked.connect(save)
    dlg.btn_cancel.clicked.connect(dlg.reject)
    dlg.exec_()


def open_change_password_dialog(parent, user):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Changer mon mot de passe")
    dlg.resize(380, 200)
    dlg.setMinimumSize(340, 170)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    old = QLineEdit()
    old.setEchoMode(QLineEdit.Password)
    new = QLineEdit()
    new.setEchoMode(QLineEdit.Password)
    confirm = QLineEdit()
    confirm.setEchoMode(QLineEdit.Password)
    form.addRow("Ancien mot de passe :", old)
    form.addRow("Nouveau mot de passe :", new)
    form.addRow("Confirmer :", confirm)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    if dlg.exec_() == QDialog.Accepted:
        if not new.text() or new.text() != confirm.text():
            QMessageBox.warning(dlg, "Mot de passe",
                                "Les nouveaux mots de passe ne correspondent pas.")
            return
        ok, message = auth.change_password(user["id"], old.text(), new.text())
        QMessageBox.information(dlg, "Mot de passe", message)


def open_reset_password_dialog(parent, ctx):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Reinitialiser un mot de passe")
    dlg.resize(400, 180)
    dlg.setMinimumSize(340, 150)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    combo = QComboBox()
    for u in repos.utilisateurs():
        if u["role"] in ("directeur", "gestionnaire"):
            combo.addItem(f"{u['nom_complet']} ({u['role']})", u["id"])
    new_pwd = QLineEdit(auth.random_password())
    if combo.count() == 0:
        QMessageBox.information(dlg, "Mot de passe",
                                "Aucun compte disponible a reinitialiser.")
        return
    form.addRow("Compte :", combo)
    form.addRow("Nouveau mot de passe :", new_pwd)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    if dlg.exec_() == QDialog.Accepted:
        if not new_pwd.text().strip():
            QMessageBox.warning(dlg, "Mot de passe", "Mot de passe vide.")
            return
        repos.reset_password(combo.currentData(), hash_password(new_pwd.text()))
        QMessageBox.information(dlg, "Mot de passe", "Mot de passe reinitialise.")
