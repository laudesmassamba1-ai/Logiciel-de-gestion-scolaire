from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QComboBox, QFormLayout, QDoubleSpinBox, QCheckBox, QPushButton, QTabWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from repositories import repos
from ui.pages.helpers import (
    _btn, _simple_btn_style, _reload_combo, _add_btn, _make_table,
    _page_header,
)
from core.config import (
    C_EMPTY_STATE, STYLE_BTN_PRIMARY, STYLE_TABLE,
    C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_RED, C_RED_BG, C_RED_BORDER, C_TEXT_MUTED, C_BORDER,
    C_BG_ALT,
)


def programmes(page, ctx):
    if page.layout() is not None:
        return
    page.setStyleSheet("")
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)
    lay.setSpacing(16)
    _page_header(lay, "Matieres & Programmes",
                 "Matieres enseignees et affectations par classe")

    tabs = QTabWidget()
    lay.addWidget(tabs)

    onglet_matieres = QWidget()
    lay_m = QVBoxLayout(onglet_matieres)
    top_m = QHBoxLayout()
    btn_add_matiere = _add_btn("+ Nouvelle Matiere", lambda: open_matiere_dialog(page, ctx, fill_m))
    top_m.addStretch(1)
    if ctx.can_edit("programmes"):
        top_m.addWidget(btn_add_matiere)
    lay_m.addLayout(top_m)
    table_m = _make_table(["Nom", "Coefficient", "Actions"])
    lay_m.addWidget(table_m)
    lbl_empty_m = QLabel("Aucune matiere enregistree")
    lbl_empty_m.setStyleSheet(f"color: {C_EMPTY_STATE}; padding: 30px;")
    lbl_empty_m.setAlignment(Qt.AlignCenter)
    lay_m.addWidget(lbl_empty_m)

    def fill_m():
        rows = repos.matieres()
        table_m.setRowCount(len(rows))
        for i, mt in enumerate(rows):
            table_m.setItem(i, 0, QTableWidgetItem(mt["nom"]))
            table_m.setItem(i, 1, QTableWidgetItem(str(mt["coefficient"])))
            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(2, 2, 2, 2)
            if ctx.can_edit("programmes"):
                cl.addWidget(_btn("Modifier", partial(open_matiere_dialog, page, ctx, fill_m, mt),
                                   _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER)))
                cl.addWidget(_btn("Supprimer", partial(_delete_matiere, page, ctx, mt),
                                   _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)))
            table_m.setCellWidget(i, 2, cell)
        table_m.resizeColumnsToContents()
        lbl_empty_m.setVisible(not rows)
        table_m.setVisible(bool(rows))

    def _delete_matiere(parent, ctx, mt):
        if QMessageBox.question(parent, "Matiere",
                                f"Supprimer la matiere {mt['nom']} ?") == QMessageBox.Yes:
            repos.delete_matiere(mt["id"])
            fill_m()

    tabs.addTab(onglet_matieres, "Matieres")

    onglet_affect = QWidget()
    lay_a = QVBoxLayout(onglet_affect)

    top_a = QHBoxLayout()
    combo_cycle_a = QComboBox()
    combo_cycle_a.addItem("Tous les cycles", None)
    for cyc in repos.cycles():
        combo_cycle_a.addItem(cyc["nom"], cyc["id"])
    combo_classe_a = QComboBox()
    top_a.addWidget(QLabel("Cycle :"))
    top_a.addWidget(combo_cycle_a)
    top_a.addWidget(QLabel("Classe :"))
    top_a.addWidget(combo_classe_a)
    top_a.addStretch(1)
    lay_a.addLayout(top_a)

    row_btn = QHBoxLayout()
    btn_tout_cocher = _btn("Tout cocher", lambda: _set_checks(True),
                            _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER))
    btn_tout_decocher = _btn("Tout decocher", lambda: _set_checks(False),
                              _simple_btn_style(bg=C_BG_ALT, fg=C_TEXT_MUTED, border=C_BORDER))
    row_btn.addWidget(btn_tout_cocher)
    row_btn.addWidget(btn_tout_decocher)
    row_btn.addStretch(1)
    btn_save_prog = QPushButton("Enregistrer le programme")
    btn_save_prog.setCursor(Qt.PointingHandCursor)
    btn_save_prog.setStyleSheet(STYLE_BTN_PRIMARY)
    if ctx.can_edit("programmes"):
        row_btn.addWidget(btn_save_prog)
    lay_a.addLayout(row_btn)

    table_a = _make_table(["", "Matiere", "Coefficient", "Enseignant"])
    table_a.setColumnWidth(0, 40)
    lay_a.addWidget(table_a)
    lbl_empty_a = QLabel("Aucune matiere enregistree. Ajoutez d'abord des matieres.")
    lbl_empty_a.setStyleSheet(f"color: {C_EMPTY_STATE}; padding: 30px;")
    lbl_empty_a.setAlignment(Qt.AlignCenter)
    lay_a.addWidget(lbl_empty_a)

    lignes = []

    def _fill_classes():
        _reload_combo(combo_cycle_a,
                      [("Tous les cycles", None)] + [(c["nom"], c["id"]) for c in repos.cycles()])
        cycle_id = combo_cycle_a.currentData()
        combo_classe_a.blockSignals(True)
        combo_classe_a.clear()
        for c in repos.classes():
            if cycle_id is not None and c.get("cycle_id") != cycle_id:
                continue
            combo_classe_a.addItem(c["nom"], c["id"])
        combo_classe_a.blockSignals(False)
        refresh_a()

    def refresh_a():
        classe_id = combo_classe_a.currentData()
        matieres = repos.matieres()
        existants = {p["matiere_id"]: p for p in repos.programmes(classe_id)} if classe_id else {}
        personnel_list = repos.personnel()
        table_a.setRowCount(len(matieres))
        lignes.clear()
        for i, mt in enumerate(matieres):
            en_prog = mt["id"] in existants
            check = QCheckBox()
            check.setChecked(en_prog)
            table_a.setCellWidget(i, 0, check)
            table_a.setItem(i, 1, QTableWidgetItem(mt["nom"]))
            coeff = QDoubleSpinBox()
            coeff.setRange(0.5, 10.0)
            coeff.setDecimals(1)
            coeff.setValue(float(existants[mt["id"]]["coefficient"]) if en_prog
                           else float(mt["coefficient"] or 1))
            coeff.setEnabled(en_prog)
            table_a.setCellWidget(i, 2, coeff)
            ens = QComboBox()
            ens.addItem("-- Non affecte --", None)
            for p in personnel_list:
                ens.addItem(p["nom_complet"], p["id"])
            if en_prog and existants[mt["id"]].get("enseignant_id"):
                idx = ens.findData(existants[mt["id"]]["enseignant_id"])
                if idx >= 0:
                    ens.setCurrentIndex(idx)
            ens.setEnabled(en_prog)
            table_a.setCellWidget(i, 3, ens)
            check.toggled.connect(lambda on, c=coeff, e=ens: (c.setEnabled(on), e.setEnabled(on)))
            lignes.append({"id": mt["id"], "check": check, "coeff": coeff, "ens": ens})
        table_a.resizeColumnsToContents()
        lbl_empty_a.setVisible(not matieres)
        table_a.setVisible(bool(matieres))

    def _set_checks(checked):
        for ligne in lignes:
            ligne["check"].setChecked(checked)

    def save_prog():
        classe_id = combo_classe_a.currentData()
        if not classe_id:
            QMessageBox.warning(page, "Programme", "Choisissez d'abord une classe.")
            return
        existants = {p["matiere_id"]: p for p in repos.programmes(classe_id)}
        for ligne in lignes:
            if ligne["check"].isChecked():
                repos.save_programme(classe_id, ligne["id"],
                                     ligne["ens"].currentData(), ligne["coeff"].value())
            elif ligne["id"] in existants:
                repos.delete_programme(existants[ligne["id"]]["id"])
        QMessageBox.information(page, "Programme", "Programme de la classe enregistre.")
        refresh_a()

    combo_cycle_a.currentIndexChanged.connect(_fill_classes)
    combo_classe_a.currentIndexChanged.connect(refresh_a)
    btn_save_prog.clicked.connect(save_prog)
    tabs.addTab(onglet_affect, "Programme par Classe")

    fill_m()
    _fill_classes()
    page.refresh = lambda: (fill_m(), _fill_classes())


def open_matiere_dialog(parent, ctx, on_created, matiere=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouvelle Matiere" if not matiere else "Modifier la Matiere")
    dlg.resize(380, 180)
    dlg.setMinimumSize(340, 150)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    nom = QLineEdit()
    coeff = QDoubleSpinBox()
    coeff.setRange(0.5, 10.0)
    coeff.setDecimals(1)
    coeff.setValue(1.0)
    if matiere:
        nom.setText(matiere["nom"])
        coeff.setValue(float(matiere["coefficient"] or 1))
    form.addRow("Nom :", nom)
    form.addRow("Coefficient :", coeff)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    if dlg.exec_() == QDialog.Accepted:
        if not nom.text().strip():
            QMessageBox.warning(dlg, "Matiere", "Le nom est obligatoire.")
            return
        if matiere:
            repos.update_matiere(matiere["id"], nom.text().strip(), coeff.value())
        else:
            repos.add_matiere(nom.text().strip(), coeff.value())
        if on_created:
            on_created()
