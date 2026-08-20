from functools import partial

from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QComboBox,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from repositories import repos
from ui.loader import apply_ui
from core.config import C_RED, C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_RED_BG, C_RED_BORDER, C_TEXT_SECONDARY
from ui.pages.helpers import (
    _btn, _simple_btn_style, _classe_items, _reload_combo, _fit_rows,
)


def classes(page, ctx):
    if page.layout() is not None:
        return
    apply_ui("classes/classes.ui", page)
    _fit_rows(page.table_classes)
    page.table_classes.insertColumn(6)
    page.table_classes.setHorizontalHeaderItem(6, QTableWidgetItem("Cycle"))

    def fill():
        _reload_combo(page.combo_filter_niveau,
                      [("Tous les niveaux", None)] +
                      [(n, n) for n in sorted({c["niveau"] for c in repos.classes() if c.get("niveau")})])
        recherche = page.input_search_classe.text().strip().lower()
        niveau = page.combo_filter_niveau.currentData()
        all_rows = repos.classes()
        rows = all_rows
        if recherche:
            rows = [c for c in rows if recherche in c["nom"].lower()]
        if niveau:
            rows = [c for c in rows if c["niveau"] == niveau]
        page.table_classes.setRowCount(len(rows))
        for i, c in enumerate(rows):
            effectif = c["effectif"]
            capacite = c["capacite"]
            values = [c["nom"], c["niveau"] or "-", effectif, capacite,
                      c["titulaire"] or "-", c["salle"] or "-",
                      c.get("cycle_nom") or "-"]
            for j, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if j == 2 and capacite and effectif >= capacite:
                    item.setForeground(QBrush(QColor(C_RED)))
                    item.setToolTip("Classe complete")
                page.table_classes.setItem(i, j, item)
            cell = QWidget()
            lay = QHBoxLayout(cell)
            lay.setContentsMargins(2, 2, 2, 2)
            lay.addWidget(_btn("Modifier", partial(open_classe_dialog, page, ctx, c),
                                _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER)))
            lay.addWidget(_btn("Supprimer", partial(_delete_classe, page, ctx, c),
                                _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)))
            page.table_classes.setCellWidget(i, 7, cell)
        page._classe_rows = rows
        page.table_classes.resizeColumnsToContents()
        page.table_classes.horizontalHeader().setStretchLastSection(True)
        page.table_classes.horizontalHeader().setMinimumSectionSize(80)
        page.lbl_empty_state_classes.setVisible(not rows)
        page.table_classes.setVisible(bool(rows))

        page.lbl_kpi1_valeur.setText(str(len(all_rows)))
        page.lbl_kpi2_valeur.setText(str(sum(c["effectif"] for c in all_rows)))
        page.lbl_kpi3_valeur.setText(str(len([c for c in all_rows if c["effectif"] >= c["capacite"]])))
        page.lbl_kpi4_valeur.setText(str(len([c for c in all_rows if not c.get("titulaire")])))

    def _delete_classe(parent, ctx, c):
        if QMessageBox.question(parent, "Supprimer",
                                f"Supprimer la classe {c['nom']} et ses eleves ?") \
                == QMessageBox.Yes:
            repos.delete_classe(c["id"])
            fill()

    page.btn_add_classe.clicked.connect(lambda: open_classe_dialog(page, ctx))
    page.btn_apply_filter_classe.clicked.connect(fill)
    page.input_search_classe.textChanged.connect(fill)
    page.combo_filter_niveau.currentIndexChanged.connect(fill)

    def double_clicked(row, _col):
        if 0 <= row < len(getattr(page, "_classe_rows", [])):
            open_classe_dialog(page, ctx, page._classe_rows[row])

    page.table_classes.cellDoubleClicked.connect(double_clicked)
    page.table_classes.setToolTip("Double-cliquez sur une ligne pour modifier la classe")

    fill()
    page.refresh = fill


def open_classe_dialog(parent, ctx, classe=None, on_created=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouvelle Classe" if not classe else "Modifier la Classe")
    dlg.resize(460, 480)
    dlg.setMinimumSize(380, 400)
    apply_ui("classes/classe_dialog.ui", dlg)

    combo_cycle = QComboBox()
    combo_cycle.addItem("-- Sans cycle --", None)
    for cyc in repos.cycles():
        combo_cycle.addItem(cyc["nom"], cyc["id"])
    lbl_cycle = QLabel("Cycle :")
    lbl_cycle.setStyleSheet(f"color: {C_TEXT_SECONDARY}; font-weight: bold; font-size: 12px;")
    dlg.mainLayout.insertWidget(5, lbl_cycle)
    dlg.mainLayout.insertWidget(6, combo_cycle)

    personnel = repos.personnel()
    dlg.combo_titulaire.clear()
    dlg.combo_titulaire.addItem("-- A affecter plus tard --", None)
    for p in personnel:
        dlg.combo_titulaire.addItem(p["nom_complet"], p["nom_complet"])

    if classe:
        dlg.lbl_dialog_title.setText("Modifier la Classe")
        dlg.input_nom_classe.setText(classe["nom"])
        idx = dlg.combo_niveau.findText(classe["niveau"]) if classe["niveau"] else -1
        if idx >= 0:
            dlg.combo_niveau.setCurrentIndex(idx)
        dlg.input_capacite.setValue(classe["capacite"] or 50)
        dlg.input_salle.setText(classe["salle"] or "")
        if classe.get("titulaire"):
            idx = dlg.combo_titulaire.findData(classe["titulaire"])
            if idx >= 0:
                dlg.combo_titulaire.setCurrentIndex(idx)
        idx = combo_cycle.findData(classe.get("cycle_id"))
        if idx >= 0:
            combo_cycle.setCurrentIndex(idx)

    def save():
        nom = dlg.input_nom_classe.text().strip()
        if not nom:
            QMessageBox.warning(dlg, "Classe", "Le nom de la classe est obligatoire.")
            return
        titulaire = dlg.combo_titulaire.currentData()
        if classe:
            repos.update_classe(classe["id"], nom, dlg.combo_niveau.currentText(),
                                dlg.input_capacite.value(), dlg.input_salle.text().strip(),
                                titulaire, combo_cycle.currentData())
        else:
            repos.add_classe(nom, dlg.combo_niveau.currentText(),
                             dlg.input_capacite.value(), dlg.input_salle.text().strip(),
                             titulaire, combo_cycle.currentData())
        if on_created:
            on_created()
        dlg.accept()

    dlg.btn_save.clicked.connect(save)
    dlg.btn_cancel.clicked.connect(dlg.reject)
    dlg.exec_()
