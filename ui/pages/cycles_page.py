from functools import partial

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QCheckBox, QFormLayout, QTabWidget, QTableWidgetItem, QVBoxLayout,
    QComboBox, QDateEdit, QWidget,
)

from repositories import repos
from ui.pages.helpers import (
    _btn, _simple_btn_style, _add_btn, _make_table, _page_header,
)
from core.config import C_EMPTY_STATE, C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_GOLD, C_GOLD_BG, C_GOLD_BORDER, C_RED, C_RED_BG, C_RED_BORDER


def cycles_annees(page, ctx):
    if page.layout() is not None:
        return
    page.setStyleSheet("")
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)
    _page_header(lay, "Cycles & Annees Scolaires",
                 "Cycles pedagogiques et annees scolaires de l'établissement")

    tabs = QTabWidget()
    lay.addWidget(tabs)

    page_cycles = QWidget()
    lay_cycles = QVBoxLayout(page_cycles)
    top_c = QHBoxLayout()
    btn_add_cycle = _add_btn("+ Nouveau Cycle", lambda: open_cycle_dialog(page, ctx, None, fill_cycles))
    top_c.addStretch(1)
    if ctx.can_edit("cycles"):
        top_c.addWidget(btn_add_cycle)
    lay_cycles.addLayout(top_c)
    table_cycles = _make_table(["Nom", "Description", "Actions"])
    lay_cycles.addWidget(table_cycles)
    lbl_empty_cycles = QLabel("Aucun cycle enregistre")
    lbl_empty_cycles.setStyleSheet(f"color: {C_EMPTY_STATE}; padding: 30px;")
    lbl_empty_cycles.setAlignment(Qt.AlignCenter)
    lay_cycles.addWidget(lbl_empty_cycles)

    def fill_cycles():
        rows = repos.cycles()
        table_cycles.setRowCount(len(rows))
        for i, c in enumerate(rows):
            table_cycles.setItem(i, 0, QTableWidgetItem(c["nom"]))
            table_cycles.setItem(i, 1, QTableWidgetItem(c["description"] or "-"))
            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(2, 2, 2, 2)
            cl.addWidget(_btn("Modifier", partial(open_cycle_dialog, page, ctx, c, fill_cycles),
                              _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER)))
            cl.addWidget(_btn("Supprimer", partial(_delete_cycle, page, ctx, c),
                                  _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)))
            table_cycles.setCellWidget(i, 2, cell)
        table_cycles.resizeColumnsToContents()
        lbl_empty_cycles.setVisible(not rows)
        table_cycles.setVisible(bool(rows))

    def _delete_cycle(parent, ctx, c):
        if QMessageBox.question(parent, "Cycle",
                                f"Supprimer le cycle {c['nom']} ?") == QMessageBox.Yes:
            repos.delete_cycle(c["id"])
            fill_cycles()

    tabs.addTab(page_cycles, "Cycles")

    page_annees = QWidget()
    lay_annees = QVBoxLayout(page_annees)
    top_a = QHBoxLayout()
    btn_add_annee = _add_btn("+ Nouvelle Annee", lambda: open_annee_dialog(page, ctx, None, fill_annees))
    top_a.addStretch(1)
    if ctx.can_edit("cycles"):
        top_a.addWidget(btn_add_annee)
    lay_annees.addLayout(top_a)
    table_annees = _make_table(["Libelle", "Debut", "Fin", "Active", "Actions"])
    lay_annees.addWidget(table_annees)
    lbl_empty_annees = QLabel("Aucune annee scolaire enregistree")
    lbl_empty_annees.setStyleSheet(f"color: {C_EMPTY_STATE}; padding: 30px;")
    lbl_empty_annees.setAlignment(Qt.AlignCenter)
    lay_annees.addWidget(lbl_empty_annees)

    def fill_annees():
        rows = repos.annees_scolaires()
        table_annees.setRowCount(len(rows))
        for i, a in enumerate(rows):
            table_annees.setItem(i, 0, QTableWidgetItem(a["libelle"]))
            table_annees.setItem(i, 1, QTableWidgetItem(a["date_debut"] or "-"))
            table_annees.setItem(i, 2, QTableWidgetItem(a["date_fin"] or "-"))
            table_annees.setItem(i, 3, QTableWidgetItem("Oui" if a["est_active"] else "Non"))
            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(2, 2, 2, 2)
            if not a["est_active"] and ctx.can_edit("cycles"):
                cl.addWidget(_btn("Activer", partial(_set_active, page, ctx, a),
                                  _simple_btn_style(bg=C_GOLD_BG, fg=C_GOLD, border=C_GOLD_BORDER)))
            if not a["est_active"]:
                cl.addWidget(_btn("Supprimer", partial(_delete_annee, page, ctx, a),
                              _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)))
            table_annees.setCellWidget(i, 4, cell)
        table_annees.resizeColumnsToContents()
        lbl_empty_annees.setVisible(not rows)
        table_annees.setVisible(bool(rows))

    def _set_active(parent, ctx, a):
        repos.set_annee_active(a["id"])
        fill_annees()

    def _delete_annee(parent, ctx, a):
        if QMessageBox.question(parent, "Annee",
                                f"Supprimer l'annee {a['libelle']} ?") == QMessageBox.Yes:
            repos.delete_annee_scolaire(a["id"])
            fill_annees()

    tabs.addTab(page_annees, "Annees Scolaires")

    fill_cycles()
    fill_annees()
    page.refresh = lambda: (fill_cycles(), fill_annees())


def open_cycle_dialog(parent, ctx, cycle=None, on_created=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouveau Cycle" if not cycle else "Modifier le Cycle")
    dlg.resize(420, 200)
    dlg.setMinimumSize(360, 170)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    nom = QLineEdit()
    description = QLineEdit()
    if cycle:
        nom.setText(cycle["nom"])
        description.setText(cycle["description"] or "")
    form.addRow("Nom :", nom)
    form.addRow("Description :", description)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    if dlg.exec_() == QDialog.Accepted:
        if not nom.text().strip():
            QMessageBox.warning(dlg, "Cycle", "Le nom du cycle est obligatoire.")
            return
        if cycle:
            repos.update_cycle(cycle["id"], nom.text().strip(), description.text().strip())
        else:
            repos.add_cycle(nom.text().strip(), description.text().strip())
        if on_created:
            on_created()


def open_annee_dialog(parent, ctx, annee=None, on_created=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouvelle Annee Scolaire" if not annee else "Modifier l'Annee Scolaire")
    dlg.resize(420, 260)
    dlg.setMinimumSize(360, 220)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    libelle = QLineEdit()
    libelle.setPlaceholderText("Ex: 2025-2026")
    debut = QDateEdit()
    debut.setDisplayFormat("dd/MM/yyyy")
    debut.setCalendarPopup(True)
    fin = QDateEdit()
    fin.setDisplayFormat("dd/MM/yyyy")
    fin.setCalendarPopup(True)
    active = QCheckBox("Annee scolaire active")
    if annee:
        libelle.setText(annee["libelle"])
        if annee["date_debut"]:
            debut.setDate(QDate.fromString(annee["date_debut"], "yyyy-MM-dd"))
        if annee["date_fin"]:
            fin.setDate(QDate.fromString(annee["date_fin"], "yyyy-MM-dd"))
        active.setChecked(bool(annee["est_active"]))
    form.addRow("Libelle :", libelle)
    form.addRow("Date de debut :", debut)
    form.addRow("Date de fin :", fin)
    lay.addLayout(form)
    lay.addWidget(active)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    if dlg.exec_() == QDialog.Accepted:
        if not libelle.text().strip():
            QMessageBox.warning(dlg, "Annee", "Le libelle est obligatoire.")
            return
        if annee:
            repos.update_annee_scolaire(annee["id"], libelle.text().strip(),
                                        debut.date().toString("yyyy-MM-dd"),
                                        fin.date().toString("yyyy-MM-dd"),
                                        active.isChecked())
            if active.isChecked():
                repos.set_annee_active(annee["id"])
        else:
            new_id = repos.add_annee_scolaire(
                libelle.text().strip(),
                debut.date().toString("yyyy-MM-dd"),
                fin.date().toString("yyyy-MM-dd"),
                active.isChecked())
            if active.isChecked():
                repos.set_annee_active(new_id)
        if on_created:
            on_created()
