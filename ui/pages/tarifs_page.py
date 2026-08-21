from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QComboBox, QFormLayout, QDoubleSpinBox, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from repositories import repos
from ui.loader import apply_ui
from ui.pages.helpers import (
    _btn, _simple_btn_style, _money_edit, _classe_items, _reload_combo,
    _add_btn, _kpi_card, _make_table, _page_header,
)
from ui.widgets import fmt_money
from core.config import C_EMPTY_STATE, C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_WARNING, C_RED, C_RED_BG, C_RED_BORDER


def tarifs(page, ctx):
    if page.layout() is not None:
        return
    page.setStyleSheet("")
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)
    _page_header(lay, "Tarifs & Scolarite", "Montants des frais par classe et par type")

    filtre = QHBoxLayout()
    combo_classe = QComboBox()
    combo_classe.addItem("Toutes les classes", None)
    for c in repos.classes():
        combo_classe.addItem(c["nom"], c["id"])
    filtre.addWidget(QLabel("Classe :"))
    filtre.addWidget(combo_classe)
    filtre.addStretch(1)
    btn_add_tarif = _add_btn("+ Nouveau Tarif", lambda: open_tarif_dialog(page, ctx, refresh))
    if ctx.can_edit("tarifs"):
        filtre.addWidget(btn_add_tarif)
    lay.addLayout(filtre)

    kpi_lay = QHBoxLayout()
    lbl_kpi_nb = _kpi_card("Nombre de tarifs", "0")
    lbl_kpi_moy = _kpi_card("Montant moyen", "0 FCFA", C_BLUE)
    lbl_kpi_min = _kpi_card("Tarif minimum", "0 FCFA", C_WARNING)
    lbl_kpi_max = _kpi_card("Tarif maximum", "0 FCFA", C_RED)
    for w in (lbl_kpi_nb, lbl_kpi_moy, lbl_kpi_min, lbl_kpi_max):
        kpi_lay.addWidget(w)
    lay.addLayout(kpi_lay)

    table = _make_table(["Classe", "Type de frais", "Montant", "Annee scolaire", "Actions"])
    lay.addWidget(table)
    lbl_empty = QLabel("Aucun tarif enregistre")
    lbl_empty.setStyleSheet(f"color: {C_EMPTY_STATE}; padding: 30px;")
    lbl_empty.setAlignment(Qt.AlignCenter)
    lay.addWidget(lbl_empty)

    def refresh():
        _reload_combo(combo_classe, _classe_items())
        classe_id = combo_classe.currentData()
        rows = repos.tarifs(classe_id=classe_id)
        table.setRowCount(len(rows))
        for i, t in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(t["classe_nom"] or "-"))
            table.setItem(i, 1, QTableWidgetItem(t["type_frais"]))
            table.setItem(i, 2, QTableWidgetItem(fmt_money(t["montant"])))
            table.setItem(i, 3, QTableWidgetItem(t["annee_scolaire"] or "-"))
            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(2, 2, 2, 2)
            if ctx.can_edit("tarifs"):
                cl.addWidget(_btn("Modifier", partial(open_tarif_dialog, page, ctx, refresh, t),
                                   _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER)))
                cl.addWidget(_btn("Supprimer", partial(_delete_tarif, page, ctx, t),
                                   _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)))
            table.setCellWidget(i, 4, cell)
        table.resizeColumnsToContents()
        lbl_empty.setVisible(not rows)
        table.setVisible(bool(rows))
        if rows:
            montants = [float(t["montant"]) for t in rows]
            lbl_kpi_nb.findChild(QLabel, "kpi_value").setText(str(len(rows)))
            lbl_kpi_moy.findChild(QLabel, "kpi_value").setText(fmt_money(sum(montants) / len(montants)))
            lbl_kpi_min.findChild(QLabel, "kpi_value").setText(fmt_money(min(montants)))
            lbl_kpi_max.findChild(QLabel, "kpi_value").setText(fmt_money(max(montants)))
        else:
            lbl_kpi_nb.findChild(QLabel, "kpi_value").setText("0")
            lbl_kpi_moy.findChild(QLabel, "kpi_value").setText("0 FCFA")
            lbl_kpi_min.findChild(QLabel, "kpi_value").setText("0 FCFA")
            lbl_kpi_max.findChild(QLabel, "kpi_value").setText("0 FCFA")

    def _delete_tarif(parent, ctx, t):
        if QMessageBox.question(parent, "Tarif",
                                f"Supprimer le tarif {t['type_frais']} ({t['classe_nom']}) ?") \
                == QMessageBox.Yes:
            repos.delete_tarif(t["id"])
            refresh()

    combo_classe.currentIndexChanged.connect(refresh)
    refresh()
    page.refresh = refresh


def open_tarif_dialog(parent, ctx, on_created, tarif=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouveau Tarif" if not tarif else "Modifier le Tarif")
    dlg.resize(440, 260)
    dlg.setMinimumSize(380, 220)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    combo_classe = QComboBox()
    for c in repos.classes():
        combo_classe.addItem(c["nom"], c["id"])
    type_frais = QComboBox()
    type_frais.setEditable(True)
    type_frais.addItems(["Scolarite", "Inscription", "Tenues", "Transport", "Cantine", "Autres"])
    montant = _money_edit(minimum=1)
    annee = QLineEdit()
    active = repos.annee_scolaire_active()
    annee.setText(active["libelle"] if active else "")
    if tarif:
        idx = combo_classe.findData(tarif["classe_id"])
        if idx >= 0:
            combo_classe.setCurrentIndex(idx)
        idx = type_frais.findText(tarif["type_frais"])
        if idx >= 0:
            type_frais.setCurrentIndex(idx)
        else:
            type_frais.setEditText(tarif["type_frais"])
        montant.setValue(float(tarif["montant"]))
        annee.setText(tarif["annee_scolaire"] or "")
    form.addRow("Classe :", combo_classe)
    form.addRow("Type de frais :", type_frais)
    form.addRow("Montant :", montant)
    form.addRow("Annee scolaire :", annee)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    btn_ok = buttons.button(QDialogButtonBox.Ok)
    btn_ok.setText("Valider")
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    def valider():
        if combo_classe.currentData() is None:
            QMessageBox.warning(dlg, "Tarif", "Selectionnez une classe.")
            return
        if montant.value() <= 0:
            QMessageBox.warning(dlg, "Tarif", "Le montant doit etre superieur a 0.")
            return
        libelle_type = type_frais.currentText().strip()
        if not libelle_type:
            QMessageBox.warning(dlg, "Tarif", "Le type de frais est obligatoire.")
            return
        # Anti-doublon : meme classe + type + annee deja tarifé.
        existants = repos.tarifs(classe_id=combo_classe.currentData())
        for t in existants:
            meme = (t["type_frais"].lower() == libelle_type.lower()
                    and (t["annee_scolaire"] or "") == annee.text().strip()
                    and (not tarif or t["id"] != tarif["id"]))
            if meme:
                reponse = QMessageBox.question(
                    dlg, "Tarif",
                    "Un tarif identique existe deja pour cette classe, ce type "
                    "et cette annee. Le remplacer ?")
                if reponse != QMessageBox.Yes:
                    return
                repos.delete_tarif(t["id"])
                break
        if tarif:
            repos.update_tarif(tarif["id"], combo_classe.currentData(),
                               libelle_type, montant.value(), annee.text().strip())
        else:
            repos.add_tarif(combo_classe.currentData(), libelle_type,
                            montant.value(), annee.text().strip())
        dlg.accept()

    btn_ok.clicked.connect(valider)

    dlg.exec_()
    if dlg.result() == QDialog.Accepted and on_created:
        on_created()
