from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QLineEdit, QMessageBox,
    QComboBox, QFormLayout, QPushButton, QTableWidgetItem, QVBoxLayout,
)

from repositories import repos
from services import reports
from ui import toast
from ui.pages.helpers import (
    _classe_items, _reload_combo,
)
from ui.widgets.page_templates import ListPageTemplate
from core.config import (
    CRENEAUX, STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY,
)

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]


class PlanningCellDialog(QDialog):
    def __init__(self, parent, jour, creneau, matieres, current=None):
        super().__init__(parent)
        self.setWindowTitle(f"{jour} - {creneau}")
        self.resize(320, 120)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.combo = QComboBox()
        self.combo.addItem("-- Libre --", None)
        for m in matieres:
            self.combo.addItem(m["nom"], m["nom"])
        self.salle = QLineEdit()
        self.salle.setPlaceholderText("Salle")
        if current:
            matiere = current.get("matiere")
            if matiere:
                idx = self.combo.findData(matiere)
                if idx >= 0:
                    self.combo.setCurrentIndex(idx)
            self.salle.setText(current.get("salle") or "")
        form.addRow("Matiere :", self.combo)
        form.addRow("Salle :", self.salle)
        lay.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def values(self):
        return self.combo.currentData(), self.salle.text().strip()


def _creneau(table, row):
    item = table.verticalHeaderItem(row)
    return item.text() if item else CRENEAUX[row]


def _jour(table, col):
    item = table.horizontalHeaderItem(col)
    return item.text() if item else JOURS[col]


def planning(page, ctx):
    if page.layout() is not None:
        return
    tpl = ListPageTemplate(page, "Planning",
                           "Emploi du temps par classe (edit : double-clic)")
    peut_editer = ctx.can_edit("planning")

    combo_classe = QComboBox()
    tpl.ajouter_filtre(QLabel("Classe :"))
    tpl.ajouter_filtre(combo_classe)
    tpl.ajouter_space_filtre()

    table = tpl.table
    table.setColumnCount(len(JOURS))
    table.setHorizontalHeaderLabels(JOURS)
    table.setRowCount(len(CRENEAUX))
    table.setVerticalHeaderLabels(CRENEAUX)

    btn_edit = QPushButton("Modifier")
    btn_edit.setCursor(Qt.PointingHandCursor)
    btn_edit.setStyleSheet(STYLE_BTN_SECONDARY)
    btn_print = QPushButton("Imprimer")
    btn_print.setCursor(Qt.PointingHandCursor)
    btn_print.setStyleSheet(STYLE_BTN_SECONDARY)
    if peut_editer:
        tpl.header.ajouter_action(btn_edit)
    tpl.header.ajouter_action(btn_print)

    editing = {"on": False}

    def _exit_edit():
        if not editing["on"]:
            return
        editing["on"] = False
        btn_edit.setText("Modifier")
        btn_edit.setStyleSheet(STYLE_BTN_SECONDARY)

    def refresh():
        _exit_edit()
        _reload_combo(combo_classe, _classe_items(avec_toutes=False))
        classe_id = combo_classe.currentData()
        table.clearContents()
        if not classe_id:
            tpl.vide.set_message("Choisissez une classe",
                                 "Selectionnez une classe pour voir son emploi "
                                 "du temps.")
            tpl.pile.setCurrentWidget(tpl.vide)
            return
        tpl.pile.setCurrentWidget(table)
        grid = repos.planning_for(classe_id)
        for row in range(len(CRENEAUX)):
            creneau = _creneau(table, row)
            for col in range(len(JOURS)):
                jour = _jour(table, col)
                entree = grid.get((jour, creneau))
                if entree:
                    texte = entree["matiere"] or ""
                    if entree.get("salle"):
                        texte += f" ({entree['salle']})"
                    table.setItem(row, col, QTableWidgetItem(texte))
        table.refresh_height()

    def _start_edit():
        if not combo_classe.currentData():
            QMessageBox.warning(page, "Planning", "Choisissez d'abord une classe.")
            return
        editing["on"] = True
        btn_edit.setText("Enregistrer le Planning")
        btn_edit.setStyleSheet(STYLE_BTN_PRIMARY)

    def _finish_edit():
        classe_id = combo_classe.currentData()
        if not classe_id:
            QMessageBox.warning(page, "Planning", "Choisissez d'abord une classe.")
            return
        entries = []
        for row in range(len(CRENEAUX)):
            creneau = _creneau(table, row)
            if "Pause" in creneau:
                continue
            for col in range(len(JOURS)):
                jour = _jour(table, col)
                item = table.item(row, col)
                matiere = salle = None
                if item and item.text().strip():
                    texte = item.text()
                    if "(" in texte:
                        matiere, salle = texte.rsplit("(", 1)
                        matiere = matiere.strip()
                        salle = salle.rstrip(")").strip() or None
                    else:
                        matiere = texte
                    entries.append((jour, creneau, matiere, salle))
        repos.save_planning(classe_id, entries)
        editing["on"] = False
        btn_edit.setText("Modifier")
        btn_edit.setStyleSheet(STYLE_BTN_SECONDARY)
        toast.succes(page, "Emploi du temps enregistre.")
        refresh()

    def cell_double_clicked(row, col):
        if not editing["on"]:
            return
        creneau = _creneau(table, row)
        if "Pause" in creneau:
            return
        jour = _jour(table, col)
        current = {"matiere": None, "salle": None}
        item = table.item(row, col)
        if item and item.text().strip():
            texte = item.text()
            if "(" in texte:
                matiere, salle = texte.rsplit("(", 1)
                current["matiere"] = matiere.strip() or None
                current["salle"] = salle.rstrip(")").strip() or None
            else:
                current["matiere"] = texte
        dlg = PlanningCellDialog(page, jour, creneau, repos.matieres(), current)
        if dlg.exec_() == QDialog.Accepted:
            matiere, salle = dlg.values()
            texte = matiere if matiere else ""
            if matiere and salle:
                texte += f" ({salle})"
            table.setItem(row, col, QTableWidgetItem(texte))

    def print_planning():
        classe_id = combo_classe.currentData()
        classe = repos.classe_by_id(classe_id) if classe_id else None
        if not classe:
            QMessageBox.warning(page, "Planning", "Choisissez une classe.")
            return
        reports.planning(classe)

    btn_edit.clicked.connect(
        lambda: _finish_edit() if editing["on"] else _start_edit())
    table.cellDoubleClicked.connect(cell_double_clicked)
    btn_print.clicked.connect(print_planning)
    combo_classe.currentIndexChanged.connect(refresh)

    refresh()
    page.refresh = refresh
