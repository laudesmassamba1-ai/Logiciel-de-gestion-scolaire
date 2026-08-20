from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QComboBox, QFormLayout, QDoubleSpinBox, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from repositories import repos
from ui.pages.helpers import (
    _btn, _simple_btn_style, _money_edit,
)
from ui.widgets import fmt_money
from core.config import (
    STYLE_BTN_PRIMARY, STYLE_TABLE, STYLE_EMPTY_STATE,
    STYLE_HEADER_TITLE, STYLE_HEADER_SUBTITLE,
    C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_RED, C_RED_BG, C_RED_BORDER,
)


def personnel(page, ctx):
    if page.layout() is not None:
        return
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)

    header = QVBoxLayout()
    titre = QLabel("Personnel & RH")
    titre.setStyleSheet(STYLE_HEADER_TITLE)
    sub = QLabel("Enseignants, administration et salaires")
    sub.setStyleSheet(STYLE_HEADER_SUBTITLE)
    header.addWidget(titre)
    header.addWidget(sub)
    lay.addLayout(header)

    top = QHBoxLayout()
    search = QLineEdit()
    search.setPlaceholderText("Rechercher un membre du personnel...")
    top.addWidget(search)
    top.addStretch(1)
    btn_add = _btn("+ Nouvel Employe",
                   lambda: open_personnel_dialog(page, ctx),
                   STYLE_BTN_PRIMARY)
    top.addWidget(btn_add)
    lay.addLayout(top)

    from PyQt5.QtWidgets import QTableWidget
    table = QTableWidget(0, 6)
    table.setHorizontalHeaderLabels(
        ["Nom complet", "Fonction", "Telephone", "Email", "Salaire", "Actions"])
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(42)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setMinimumSectionSize(80)
    table.setStyleSheet(STYLE_TABLE)
    lay.addWidget(table)

    lbl_empty = QLabel("Aucun membre du personnel enregistre")
    lbl_empty.setStyleSheet(STYLE_EMPTY_STATE)
    lbl_empty.setAlignment(Qt.AlignCenter)
    lay.addWidget(lbl_empty)

    def fill():
        rows = repos.personnel(search.text().strip())
        table.setRowCount(len(rows))
        for i, p in enumerate(rows):
            values = [p["nom_complet"], p["fonction"] or "-", p["telephone"] or "-",
                      p["email"] or "-", fmt_money(p["salaire"])]
            for j, val in enumerate(values):
                table.setItem(i, j, QTableWidgetItem(str(val)))
            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(2, 2, 2, 2)
            cl.addWidget(_btn("Modifier", partial(open_personnel_dialog, page, ctx, p),
                              _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER)))
            cl.addWidget(_btn("Supprimer", partial(_delete, page, ctx, p),
                              _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)))
            table.setCellWidget(i, 5, cell)
        table.resizeColumnsToContents()
        lbl_empty.setVisible(not rows)
        table.setVisible(bool(rows))

    def _delete(parent, ctx, p):
        if QMessageBox.question(parent, "Personnel",
                                f"Supprimer {p['nom_complet']} ?") == QMessageBox.Yes:
            repos.delete_personnel(p["id"])
            fill()

    search.textChanged.connect(fill)
    fill()
    page.refresh = fill


def open_personnel_dialog(parent, ctx, employe=None):
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
    buttons.accepted.connect(dlg.accept)
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
    if dlg.exec_() == QDialog.Accepted:
        if not nom.text().strip():
            QMessageBox.warning(dlg, "Personnel", "Le nom est obligatoire.")
            return
        data = (nom.text().strip(), fonction.text().strip(), tel.text().strip(),
                email.text().strip(), salaire.value(), statut.currentText())
        if employe:
            repos.update_personnel(employe["id"], *data)
        else:
            repos.add_personnel(*data)
