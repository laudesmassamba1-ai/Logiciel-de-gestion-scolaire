from functools import partial

from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QLineEdit, QMessageBox,
    QComboBox, QFormLayout, QVBoxLayout,
)

from repositories import repos
from ui import toast
from ui.pages.helpers import (
    _btn, _simple_btn_style, _money_edit, _actions_cell, _adapter_hauteur,
)
from ui.widgets import fmt_money
from ui.widgets.page_templates import ListPageTemplate
from core.config import (
    STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY,
    C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_RED, C_RED_BG, C_RED_BORDER,
)


def personnel(page, ctx):
    if page.layout() is not None:
        return
    tpl = ListPageTemplate(
        page, "Personnel & RH", "Enseignants, administration et salaires")
    peut_gerer = ctx.can_edit("personnel")

    search = QLineEdit()
    search.setPlaceholderText("Rechercher un membre du personnel...")
    search.setMaximumWidth(360)
    tpl.ajouter_filtre(search)
    tpl.ajouter_space_filtre()

    tpl.table.setColumnCount(6)
    tpl.table.setHorizontalHeaderLabels(
        ["Nom complet", "Fonction", "Telephone", "Email", "Salaire", "Actions"])

    def _ouvrir_dialog(employe=None):
        open_personnel_dialog(page, ctx, employe)
        fill()  # la liste doit reflechir l'employe cree/modifie

    def _delete(parent, ctx, p):
        from ui.pages.helpers import confirmer
        if confirmer(parent, f"Supprimer {p['nom_complet']} ?", "Personnel"):
            repos.delete_personnel(p["id"])
            toast.succes(parent, "Employe supprime.")
            fill()

    def fill():
        rows = repos.personnel(search.text().strip())
        valeurs = [[p["nom_complet"], p["fonction"] or "-", p["telephone"] or "-",
                    p["email"] or "-", fmt_money(p["salaire"]), ""] for p in rows]
        tpl.remplir(
            valeurs,
            message_vide="Aucun membre du personnel enregistre",
            sous_titre_vide="Ajoutez les enseignants et l'administration "
                            "pour suivre les salaires.")
        for i, p in enumerate(rows):
            tpl.table.setCellWidget(i, 5, _actions_cell(*(
                (
                    _btn("Modifier", partial(_ouvrir_dialog, p),
                         _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER)),
                    _btn("Supprimer", partial(_delete, page, ctx, p),
                         _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)),
                ) if peut_gerer else ()
            )))
        page._personnel_rows = rows

    if peut_gerer:
        btn_add = _btn("+ Nouvel Employe", _ouvrir_dialog, STYLE_BTN_PRIMARY)
        tpl.header.ajouter_action(btn_add)
    btn_pdf = _btn("Exporter PDF", lambda: _exporter_pdf(), STYLE_BTN_SECONDARY)
    tpl.header.ajouter_action(btn_pdf)

    def _exporter_pdf():
        from services import rapports
        rows = getattr(page, "_personnel_rows", [])
        lignes = [[p["nom_complet"], p["fonction"] or "-",
                   p["telephone"] or "-", p["email"] or "-",
                   fmt_money(p["salaire"])] for p in rows]
        if not rapports.export_table_pdf(
                "Personnel et salaires",
                f"Filtres actuels - le {rapports._date_pdf()}",
                ["Nom complet", "Fonction", "Telephone", "Email", "Salaire"],
                lignes, "rapport_liste_personnel.pdf"):
            toast.info(page, "Rien a exporter : aucun employe dans ce filtre.")

    search.textChanged.connect(fill)
    fill()
    page.refresh = fill


def open_personnel_dialog(parent, ctx, employe=None):
    if ctx is not None and not ctx.can_edit("personnel"):
        QMessageBox.warning(parent, "Acces refuse",
                            "Seul le directeur peut gerer le personnel.")
        return
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouvel Employe" if not employe else "Modifier Employe")
    dlg.resize(400, 260)
    dlg.setMinimumSize(360, 220)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    nom = QLineEdit()
    fonction = QLineEdit()
    fonction.setPlaceholderText("Ex: Enseignant Mathematiques")
    tel = QLineEdit()
    email = QLineEdit()
    salaire = _money_edit()
    statut = QComboBox()
    statut.addItems(["Contrat", "CDI", "Vacataire", "Stage"])
    form.addRow("Nom complet :", nom)
    form.addRow("Fonction :", fonction)
    form.addRow("Telephone :", tel)
    form.addRow("Email :", email)
    form.addRow("Salaire :", salaire)
    form.addRow("Statut :", statut)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    if employe:
        nom.setText(employe["nom_complet"])
        fonction.setText(employe["fonction"] or "")
        tel.setText(employe["telephone"] or "")
        email.setText(employe["email"] or "")
        salaire.setValue(employe["salaire"] or 0)
        idx = statut.findText(employe["statut"] or "Contrat")
        if idx >= 0:
            statut.setCurrentIndex(idx)

    def valider():
        if not nom.text().strip():
            QMessageBox.warning(dlg, "Personnel", "Le nom est obligatoire.")
            return
        if salaire.value() <= 0:
            QMessageBox.warning(dlg, "Personnel",
                                "Le salaire doit etre superieur a 0.")
            return
        data = (nom.text().strip(), fonction.text().strip(), tel.text().strip(),
                email.text().strip(), salaire.value(), statut.currentText())
        if employe:
            repos.update_personnel(employe["id"], *data)
        else:
            repos.add_personnel(*data)
        toast.succes(dlg, "Employe enregistre.")
        dlg.accept()

    buttons.accepted.connect(valider)
    _adapter_hauteur(dlg)
    dlg.exec_()
