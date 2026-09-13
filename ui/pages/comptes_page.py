from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPushButton, QVBoxLayout, QComboBox, QFormLayout, QWidget,
)

from core.config import (ROLE_LABELS, C_GOLD, C_GOLD_BG, C_GOLD_PRESSED, C_GOLD_BORDER, C_RED, C_RED_BG, C_RED_BORDER, STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY)
from database.db import hash_password
from repositories import repos
from services import auth_service as auth
from ui import toast
from ui.loader import apply_ui
from ui.pages.helpers import (
    _btn, _simple_btn_style, _actions_cell, _adapter_hauteur,
)
from ui.widgets import KPICard
from ui.widgets.page_templates import ListPageTemplate
from resources.design_tokens import Colors


def comptes(page, ctx):
    if page.layout() is not None:
        return
    tpl = ListPageTemplate(
        page, "Comptes",
        "Utilisateurs, roles et gestion de la securite")

    combo_role = QComboBox()
    combo_role.addItems(["Tous les roles", "Directeur", "Gestionnaire"])
    search = QLineEdit()
    search.setPlaceholderText("Rechercher un utilisateur...")
    search.setMaximumWidth(360)
    tpl.ajouter_filtre(search)
    tpl.ajouter_filtre(combo_role)
    tpl.ajouter_space_filtre()

    kpi = [
        tpl.ajouter_kpi(KPICard("Comptes actifs", "0", Colors.PRIMARY), 0),
        tpl.ajouter_kpi(KPICard("Directeurs", "0", Colors.INFO), 1),
        tpl.ajouter_kpi(KPICard("Gestionnaires", "0", Colors.DANGER), 2),
        tpl.ajouter_kpi(KPICard("Comptes inactifs", "0", Colors.WARNING), 3),
    ]
    tpl.table.setColumnCount(6)
    tpl.table.setHorizontalHeaderLabels(
        ["Nom complet", "Email", "Role", "Statut", "Cree le", "Actions"])
    peut_gerer = ctx.can_edit("comptes")

    def _ouvrir_dialog():
        open_compte_dialog(page, ctx)
        fill()

    btn_add = _btn("+ Nouveau Compte", _ouvrir_dialog, STYLE_BTN_PRIMARY)
    tpl.header.ajouter_action(btn_add)

    def refresh():
        role = combo_role.currentText()
        recherche = search.text().strip()
        rows = repos.utilisateurs(role=role, recherche=recherche)
        valeurs = [[u["nom_complet"], u["email"] or "-",
                    ROLE_LABELS.get(u["role"], u["role"]),
                    "Actif" if u["actif"] else "Inactif", u["created_at"][:10], ""]
                   for u in rows]
        tpl.remplir(
            valeurs,
            message_vide="Aucun compte",
            sous_titre_vide="Modifiez votre recherche ou changez de filtre.")
        for i, u in enumerate(rows):
            if peut_gerer:
                tpl.table.setCellWidget(i, 5, _actions_cell(
                    _btn("Activer" if not u["actif"] else "Desactiver",
                         partial(_toggle, page, ctx, u),
                         _simple_btn_style(bg=C_GOLD_BG, fg=C_GOLD, border=C_GOLD_BORDER)),
                    _btn("Mdp", partial(_reset_pwd, page, ctx, u),
                         _simple_btn_style(bg=C_GOLD_BG, fg=C_GOLD_PRESSED, border=C_GOLD_BORDER)),
                    _btn("Supprimer", partial(_delete_compte, page, ctx, u),
                         _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER))))

        all_rows = repos.utilisateurs()
        actifs = [u for u in all_rows if u["actif"]]
        kpi[0].set_value(len(actifs))
        kpi[1].set_value(len([u for u in actifs if u["role"] == "directeur"]))
        kpi[2].set_value(len([u for u in actifs if u["role"] == "gestionnaire"]))
        kpi[3].set_value(len([u for u in all_rows if not u["actif"]]))

    def _est_dernier_directeur_actif(u):
        """Un compte directeur actif doit toujours en rester au moins un."""
        if u["role"] != "directeur" or not u["actif"]:
            return False
        return len([x for x in repos.utilisateurs()
                    if x["role"] == "directeur" and x["actif"]]) <= 1

    def _toggle(parent, ctx, u):
        moi = getattr(ctx, "user", None) or {}
        if u["id"] == moi.get("id"):
            QMessageBox.warning(parent, "Comptes",
                                "Vous ne pouvez pas desactiver votre propre "
                                "compte depuis cette session.")
            return
        if u["actif"] and _est_dernier_directeur_actif(u):
            QMessageBox.warning(
                parent, "Comptes",
                "Impossible de desactiver le dernier compte directeur "
                "actif : creez et activez d'abord un autre directeur.")
            return
        repos.toggle_compte(u["id"], not u["actif"])
        refresh()

    def _reset_pwd(parent, ctx, u):
        new_pwd = auth.random_password()
        from ui.pages.helpers import confirmer
        if confirmer(parent,
                     f"Reinitialiser le mot de passe de {u['nom_complet']} ?\n"
                     f"Le nouveau mot de passe sera : {new_pwd}",
                     "Reinitialisation"):
            repos.reset_password(u["id"], hash_password(new_pwd))

    def _delete_compte(parent, ctx, u):
        moi = getattr(ctx, "user", None) or {}
        if u["id"] == moi.get("id"):
            QMessageBox.warning(parent, "Comptes",
                                "Vous ne pouvez pas supprimer votre propre "
                                "compte depuis cette session.")
            return
        if _est_dernier_directeur_actif(u):
            QMessageBox.warning(
                parent, "Comptes",
                "Impossible de supprimer le dernier compte directeur "
                "actif : creez et activez d'abord un autre directeur.")
            return
        from ui.pages.helpers import confirmer
        if confirmer(parent, f"Supprimer le compte de {u['nom_complet']} ?",
                     "Supprimer"):
            repos.delete_compte(u["id"])
            refresh()

    btn_mdp = QPushButton("Changer mon mot de passe")
    btn_mdp.setCursor(Qt.PointingHandCursor)
    btn_mdp.setStyleSheet(STYLE_BTN_SECONDARY)
    btn_mdp.clicked.connect(lambda: open_change_password_dialog(page, ctx.user))
    tpl.header.ajouter_action(btn_mdp)

    search.textChanged.connect(refresh)
    combo_role.currentIndexChanged.connect(refresh)

    refresh()
    page.refresh = refresh


def open_compte_dialog(parent, ctx, compte=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouveau Compte")
    dlg.resize(440, 560)
    dlg.setMinimumSize(380, 460)
    apply_ui("comptes/compte_dialog.ui", dlg)
    dlg.combo_role_compte.clear()
    dlg.combo_role_compte.addItems(["Directeur", "Gestionnaire"])
    if compte:
        dlg.lbl_dialog_title.setText("Modifier le Compte")
        dlg.input_nom_compte.setText(compte["nom_complet"])
        idx = dlg.combo_role_compte.findText(ROLE_LABELS.get(compte["role"], ""))
        if idx >= 0:
            dlg.combo_role_compte.setCurrentIndex(idx)
        dlg.check_compte_actif.setChecked(bool(compte["actif"]))
        dlg.btn_save.setText("Enregistrer")
        dlg.lbl_field_pwd.setVisible(False)
        dlg.input_password_compte.setVisible(False)
        dlg.lbl_field_pwd2.setVisible(False)
        dlg.input_password_confirm.setVisible(False)

    def save():
        nom = dlg.input_nom_compte.text().strip()
        if not nom:
            QMessageBox.warning(dlg, "Compte",
                                "Le nom complet est obligatoire.")
            return
        role_label = dlg.combo_role_compte.currentText()
        role = {v: k for k, v in ROLE_LABELS.items()}.get(role_label, role_label.lower())
        actif = dlg.check_compte_actif.isChecked()
        if compte:
            repos.update_compte(compte["id"], nom, role, actif)
            toast.succes(dlg, "Compte mis a jour.")
            dlg.accept()
            return
        password = dlg.input_password_compte.text()
        if len(password) < 6:
            QMessageBox.warning(dlg, "Compte",
                                "Le mot de passe doit contenir au moins "
                                "6 caracteres.")
            return
        if password != dlg.input_password_confirm.text():
            QMessageBox.warning(dlg, "Compte",
                                "Les deux mots de passe ne correspondent pas.")
            return
        username = repos.add_compte(nom, role, hash_password(password), actif)
        toast.succes(dlg, f"Compte de {nom} cree.\nIdentifiant : {username}")
        dlg.accept()

    dlg.btn_save.clicked.connect(save)
    dlg.btn_cancel.clicked.connect(dlg.reject)
    _adapter_hauteur(dlg)
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

    def valider():
        if not new.text() or new.text() != confirm.text():
            QMessageBox.warning(dlg, "Mot de passe",
                                "Les nouveaux mots de passe ne correspondent pas.")
            return
        ok, message = auth.change_password(user["id"], old.text(), new.text())
        if ok:
            toast.succes(dlg, message)
            dlg.accept()
        else:
            toast.erreur(dlg, message)

    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(valider)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    dlg.exec_()


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

    def valider():
        if not new_pwd.text().strip():
            QMessageBox.warning(dlg, "Mot de passe", "Mot de passe vide.")
            return
        repos.reset_password(combo.currentData(), hash_password(new_pwd.text()))
        toast.succes(dlg, "Mot de passe reinitialise.")
        dlg.accept()

    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(valider)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    dlg.exec_()
