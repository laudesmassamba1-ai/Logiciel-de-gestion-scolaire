from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QComboBox, QFormLayout, QTableWidgetItem, QVBoxLayout,
)

from repositories import repos
from services import reports
from ui.loader import apply_ui
from ui.pages.helpers import (
    _btn, _simple_btn_style, _classe_items, _reload_combo, _fill_combos, _fit_rows,
)
from core.config import (
    CRENEAUX, STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY,
)


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


def planning(page, ctx):
    if page.layout() is not None:
        return
    apply_ui("planning/planning.ui", page)
    _fit_rows(page.table_planning)
    _fill_combos(page.combo_classe_planning, [])
    for c in repos.classes():
        page.combo_classe_planning.addItem(c["nom"], c["id"])

    editing = {"on": False}

    def _exit_edit():
        if not editing["on"]:
            return
        editing["on"] = False
        page.btn_edit_planning.setText("Modifier")
        page.btn_edit_planning.setStyleSheet(STYLE_BTN_SECONDARY)

    def refresh():
        # Changer de classe pendant l'edition : on sort du mode edition
        # pour ne jamais enregistrer les modifications dans la mauvaise classe.
        _exit_edit()
        _reload_combo(page.combo_classe_planning, _classe_items(avec_toutes=False))
        classe_id = page.combo_classe_planning.currentData()
        page.table_planning.clearContents()
        if not classe_id:
            page.lbl_empty_state_planning.setVisible(True)
            page.table_planning.setVisible(False)
            return
        page.lbl_empty_state_planning.setVisible(False)
        page.table_planning.setVisible(True)
        grid = repos.planning_for(classe_id)
        for row in range(8):
            creneau = page.table_planning.verticalHeaderItem(row).text() if \
                page.table_planning.verticalHeaderItem(row) else CRENEAUX[row]
            for col in range(6):
                jour = page.table_planning.horizontalHeaderItem(col).text()
                entree = grid.get((jour, creneau))
                if entree:
                    texte = entree["matiere"] or ""
                    if entree.get("salle"):
                        texte += f" ({entree['salle']})"
                    page.table_planning.setItem(row, col, QTableWidgetItem(texte))

    def toggle_edit():
        if editing["on"]:
            _finish_edit()
        else:
            _start_edit()

    def _start_edit():
        if not page.combo_classe_planning.currentData():
            QMessageBox.warning(page, "Planning", "Choisissez d'abord une classe.")
            return
        editing["on"] = True
        page.btn_edit_planning.setText("Enregistrer le Planning")
        page.btn_edit_planning.setStyleSheet(STYLE_BTN_PRIMARY)

    def _finish_edit():
        classe_id = page.combo_classe_planning.currentData()
        if not classe_id:
            QMessageBox.warning(page, "Planning", "Choisissez d'abord une classe.")
            return
        entries = []
        for row in range(8):
            creneau = page.table_planning.verticalHeaderItem(row).text() if \
                page.table_planning.verticalHeaderItem(row) else CRENEAUX[row]
            if "Pause" in creneau:
                continue
            for col in range(6):
                jour = page.table_planning.horizontalHeaderItem(col).text()
                item = page.table_planning.item(row, col)
                matiere = salle = None
                if item and item.text().strip():
                    texte = item.text()
                    if "(" in texte:
                        # rsplit : une matiere peut contenir des parentheses.
                        matiere, salle = texte.rsplit("(", 1)
                        matiere = matiere.strip()
                        salle = salle.rstrip(")").strip() or None
                    else:
                        matiere = texte
                    entries.append((jour, creneau, matiere, salle))
        repos.save_planning(classe_id, entries)
        editing["on"] = False
        page.btn_edit_planning.setText("Modifier")
        page.btn_edit_planning.setStyleSheet(STYLE_BTN_SECONDARY)
        QMessageBox.information(page, "Planning", "Emploi du temps enregistre.")
        refresh()

    def cell_double_clicked(row, col):
        if not editing["on"]:
            return
        creneau = page.table_planning.verticalHeaderItem(row).text() if \
            page.table_planning.verticalHeaderItem(row) else CRENEAUX[row]
        if "Pause" in creneau:
            return
        jour = page.table_planning.horizontalHeaderItem(col).text()
        current = {"matiere": None, "salle": None}
        item = page.table_planning.item(row, col)
        if item and item.text().strip():
            texte = item.text()
            if "(" in texte:
                # rsplit : une matiere peut contenir des parentheses.
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
            page.table_planning.setItem(row, col, QTableWidgetItem(texte))

    def print_planning():
        classe_id = page.combo_classe_planning.currentData()
        classe = repos.classe_by_id(classe_id) if classe_id else None
        if not classe:
            QMessageBox.warning(page, "Planning", "Choisissez une classe.")
            return
        reports.planning(classe)

    page.btn_edit_planning.clicked.connect(toggle_edit)
    page.table_planning.cellDoubleClicked.connect(cell_double_clicked)
    page.btn_print_planning.clicked.connect(print_planning)
    page.combo_classe_planning.currentIndexChanged.connect(refresh)

    refresh()
    page.refresh = refresh
