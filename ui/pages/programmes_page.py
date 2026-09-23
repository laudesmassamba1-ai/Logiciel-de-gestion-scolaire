from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QComboBox, QFormLayout, QDoubleSpinBox, QCheckBox, QPushButton, QTabWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QStackedWidget,
)

from repositories import repos
from ui import toast
from services import rapports
from ui.pages.helpers import (
    _btn, _simple_btn_style, _reload_combo, _add_btn, _actions_cell,
)
from ui.widgets import DataTable, EmptyState
from core.config import (
    STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY,
    C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_RED, C_RED_BG, C_RED_BORDER,
    C_TEXT_MUTED, C_BORDER, C_BG_ALT,
)


def programmes(page, ctx):
    if page.layout() is not None:
        return
    from ui.widgets import PageHeader
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)
    header = PageHeader(
        "Matieres & Programmes",
        "Matieres enseignees et affectations par classe")
    lay.addWidget(header)

    def _exporter_pdf():
        lignes = [[mt["nom"], str(mt["coefficient"])] for mt in repos.matieres()]
        rapports.export_table_pdf(
            "Liste des matieres",
            "Matieres enseignees et coefficients",
            ["Matiere", "Coefficient"], lignes, "rapport_matieres.pdf")

    def _exporter_programme():
        lignes = []
        for a in repos.programmes():
            lignes.append([a.get("classe_nom") or "-",
                           a.get("matiere_nom") or "-",
                           a.get("enseignant_nom") or "-"])
        rapports.export_table_pdf(
            "Programmes par classe",
            "Affectations des matieres par classe",
            ["Classe", "Matiere", "Enseignant"], lignes,
            "rapport_programmes.pdf")

    header.ajouter_action(_btn("Matieres PDF", lambda: _exporter_pdf(),
                               STYLE_BTN_SECONDARY))
    header.ajouter_action(_btn("Programme PDF", lambda: _exporter_programme(),
                               STYLE_BTN_SECONDARY))

    tabs = QTabWidget()
    lay.addWidget(tabs, 1)

    onglet_matieres = QWidget()
    lay_m = QVBoxLayout(onglet_matieres)
    table_m = DataTable()
    table_m.setColumnCount(3)
    table_m.setHorizontalHeaderLabels(["Nom", "Coefficient", "Actions"])
    vide_m = EmptyState(
        "Aucune matiere enregistree",
        "Ajoutez une matiere via le bouton ci-dessus.")
    pile_m = QStackedWidget()
    pile_m.addWidget(table_m)
    pile_m.addWidget(vide_m)
    lay_m.addWidget(pile_m, 1)

    def fill_m():
        rows = repos.matieres()
        valeurs = [[mt["nom"], str(mt["coefficient"]), ""] for mt in rows]
        table_m.remplir(valeurs)
        for i, mt in enumerate(rows):
            table_m.setCellWidget(i, 2, _actions_cell(*(
                (
                    _btn("Modifier",
                         partial(open_matiere_dialog, page, ctx, fill_m, mt),
                         _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER)),
                    _btn("Supprimer",
                         partial(_delete_matiere, page, ctx, mt),
                         _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)),
                ) if ctx.can_edit("programmes") else ()
            )))
        pile_m.setCurrentWidget(vide_m if not rows else table_m)

    def _delete_matiere(parent, ctx, mt):
        from ui.pages.helpers import confirmer
        if confirmer(
                parent,
                f"Supprimer la matiere {mt['nom']} ?\n\n"
                "Attention : toutes les notes et affectations de programme "
                "liees a cette matiere seront egalement supprimees.",
                "Matiere"):
            repos.delete_matiere(mt["id"])
            fill_m()

    def _ouvrir_matiere():
        open_matiere_dialog(page, ctx, fill_m)
        fill_m()

    btn_add_matiere = _add_btn("+ Nouvelle Matiere", _ouvrir_matiere)
    lay_m.addWidget(btn_add_matiere, 0, Qt.AlignRight)
    if not ctx.can_edit("programmes"):
        btn_add_matiere.setVisible(False)

    tabs.addTab(onglet_matieres, "Matieres")

    onglet_affect = QWidget()
    lay_a = QVBoxLayout(onglet_affect)

    top_a = QHBoxLayout()
    combo_cycle_a = QComboBox()
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

    table_a = DataTable()
    table_a.setColumnCount(4)
    table_a.setHorizontalHeaderLabels(["", "Matiere", "Coefficient", "Enseignant"])
    table_a.setColumnWidth(0, 40)
    vide_a = EmptyState(
        "Aucune matiere enregistree",
        "Ajoutez d'abord des matieres.", icone="fa5s.book")
    pile_a = QStackedWidget()
    pile_a.addWidget(table_a)
    pile_a.addWidget(vide_a)
    lay_a.addWidget(pile_a, 1)

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
        # Seuls les enseignants peuvent etre affectes a une matiere.
        enseignants_list = repos.enseignants()
        valeurs = [[None, mt["nom"], None, None] for mt in matieres]
        table_a.remplir(valeurs, largeurs=[44, 180, 100, 170])
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
            for p in enseignants_list:
                ens.addItem(p["nom_complet"], p["id"])
            if en_prog and existants[mt["id"]].get("enseignant_id"):
                idx = ens.findData(existants[mt["id"]]["enseignant_id"])
                if idx >= 0:
                    ens.setCurrentIndex(idx)
            ens.setEnabled(en_prog)
            table_a.setCellWidget(i, 3, ens)
            check.toggled.connect(lambda on, c=coeff, e=ens: (c.setEnabled(on), e.setEnabled(on)))
            lignes.append({"id": mt["id"], "check": check, "coeff": coeff, "ens": ens})
        table_a.refresh_height()
        pile_a.setCurrentWidget(vide_a if not matieres else table_a)

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
        toast.succes(page, "Programme de la classe enregistre.")
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
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    def valider():
        if not nom.text().strip():
            QMessageBox.warning(dlg, "Matiere", "Le nom est obligatoire.")
            return
        if matiere:
            repos.update_matiere(matiere["id"], nom.text().strip(), coeff.value())
        else:
            repos.add_matiere(nom.text().strip(), coeff.value())
        toast.succes(dlg, "Matiere enregistree.")
        if on_created:
            on_created()
        dlg.accept()

    buttons.accepted.connect(valider)
    dlg.exec_()
